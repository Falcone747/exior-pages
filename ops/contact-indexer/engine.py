import asyncio, hashlib, json, os, sqlite3, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import geonamescache, httpx, tldextract
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
DB=APP/'data'/'index.db'
EVIDENCE=APP/'evidence'
COUNTRIES={'US':'United States','GB':'United Kingdom','CA':'Canada','AU':'Australia','IE':'Ireland','NZ':'New Zealand'}
TERMS=['marketing agency','digital marketing agency','advertising agency','seo agency','ppc agency','performance marketing agency','social media agency','creative agency','branding agency','growth marketing agency','content marketing agency','media agency','web marketing agency']
CONTACT_HINTS=('contact','get-in-touch','get in touch','enquire','inquire','inquiry','enquiry','talk-to-us','talk to us','quote','request-a-quote','brief','start-a-project')
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')
PHONE_HINTS=('phone','telephone','mobile','tel')
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries')
HTTP_CONCURRENCY=int(os.getenv('HTTP_CONCURRENCY','60'))
CITY_MIN_POP=int(os.getenv('CITY_MIN_POP','25000'))

def conn():
    c=sqlite3.connect(DB,timeout=60); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=NORMAL'); return c

def init():
    APP.mkdir(parents=True,exist_ok=True); (APP/'data').mkdir(exist_ok=True); EVIDENCE.mkdir(exist_ok=True)
    c=conn(); c.executescript('''
    CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY,domain TEXT UNIQUE,homepage TEXT,country TEXT,source_url TEXT,discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,status TEXT DEFAULT 'DISCOVERED');
    CREATE TABLE IF NOT EXISTS forms(id INTEGER PRIMARY KEY,company_id INTEGER,page_url TEXT,signature TEXT,captcha TEXT,phone_required INTEGER,no_solicitation INTEGER,fields_json TEXT,status TEXT,UNIQUE(company_id,page_url,signature));
    CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
    CREATE INDEX IF NOT EXISTS idx_forms_status ON forms(status);
    '''); c.commit(); c.close()

def domain(url):
    try:
        x=tldextract.extract(url)
        return f'{x.domain}.{x.suffix}'.lower() if x.domain and x.suffix else None
    except Exception: return None

def add_company(d,country,source):
    if not d:return
    c=conn(); c.execute('INSERT OR IGNORE INTO companies(domain,homepage,country,source_url) VALUES(?,?,?,?)',(d,'https://'+d+'/',country,source)); c.commit(); c.close()

def cities():
    gc=geonamescache.GeonamesCache(); out={x:[] for x in COUNTRIES}
    for row in gc.get_cities().values():
        cc=row.get('countrycode'); pop=int(row.get('population') or 0)
        if cc in out and pop>=CITY_MIN_POP: out[cc].append((pop,row['name']))
    return {cc:[n for _,n in sorted(v,reverse=True)] for cc,v in out.items()}

async def discovery():
    cm=cities()
    while True:
        for cc,country in COUNTRIES.items():
            for city in cm[cc]:
                for term in TERMS:
                    q=f'"{term}" "{city}"'
                    try:
                        rows=await asyncio.to_thread(lambda:list(DDGS().text(q,max_results=20)))
                        for r in rows:
                            u=r.get('href') or r.get('url') or ''; add_company(domain(u),country,u)
                    except Exception as e: print('SEARCH_ERROR',repr(e),flush=True)
                    await asyncio.sleep(1.5)
        await asyncio.sleep(900)

async def fetch(client,url):
    try:
        r=await client.get(url,follow_redirects=True,timeout=15,headers={'User-Agent':'Mozilla/5.0 (compatible; EXIORContactIndexer/1.0)'})
        if r.status_code<400 and 'html' in r.headers.get('content-type',''): return str(r.url),r.text
    except Exception: pass
    return None,None

def candidates(base,html):
    soup=BeautifulSoup(html,'lxml'); host=urlparse(base).netloc; scored={}
    for a in soup.select('a[href]'):
        u=urljoin(base,a.get('href',''))
        if urlparse(u).netloc!=host: continue
        hay=(u+' '+a.get_text(' ',strip=True)).lower(); score=sum(1 for x in CONTACT_HINTS if x in hay)
        if score: scored[u]=max(scored.get(u,0),score)
    for p in ['/contact','/contact-us','/get-in-touch','/enquire','/inquiry','/enquiry','/request-a-quote']:
        scored.setdefault(urljoin(base,p),1)
    return [u for u,_ in sorted(scored.items(),key=lambda x:x[1],reverse=True)[:12]]

def inspect(html):
    low=html.lower(); captcha='none'
    if 'turnstile' in low: captcha='turnstile'
    elif 'hcaptcha' in low or 'h-captcha' in low: captcha='hcaptcha'
    elif 'recaptcha' in low: captcha='recaptcha'
    elif 'captcha' in low: captcha='other'
    no_sol=any(x in low for x in NO_SOLICIT)
    soup=BeautifulSoup(html,'lxml'); forms=[]
    for f in soup.find_all('form'):
        raw=str(f); sig=hashlib.sha1(raw.encode(errors='ignore')).hexdigest()[:20]; fields=[]; phone=False
        for e in f.find_all(['input','textarea','select']):
            label=' '.join([e.get('name',''),e.get('id',''),e.get('placeholder',''),e.get('aria-label','')]); req=e.has_attr('required') or e.get('aria-required')=='true'
            fields.append({'tag':e.name,'type':e.get('type',''),'label':label,'required':req})
            if req and any(x in label.lower() for x in PHONE_HINTS): phone=True
        forms.append((sig,fields,phone))
    return captcha,no_sol,forms

async def resolver():
    sem=asyncio.Semaphore(HTTP_CONCURRENCY)
    async with httpx.AsyncClient() as client:
        while True:
            c=conn(); rows=c.execute("SELECT id,domain,homepage FROM companies WHERE status='DISCOVERED' LIMIT 300").fetchall(); c.close()
            if not rows: await asyncio.sleep(5); continue
            async def one(row):
                cid,d,home=row
                async with sem:
                    base,html=await fetch(client,home)
                    if not html:
                        c=conn(); c.execute("UPDATE companies SET status='FETCH_FAILED' WHERE id=?",(cid,)); c.commit(); c.close(); return
                    found=0
                    for u in candidates(base,html):
                        page_url,page_html=await fetch(client,u)
                        if not page_html: continue
                        captcha,no_sol,forms=inspect(page_html)
                        for sig,fields,phone in forms:
                            found+=1
                            status='CONTACTABLE' if captcha=='none' and not phone and not no_sol else ('CAPTCHA' if captcha!='none' else 'PHONE_REQUIRED' if phone else 'NO_SOLICITATION')
                            c=conn(); c.execute('INSERT OR IGNORE INTO forms(company_id,page_url,signature,captcha,phone_required,no_solicitation,fields_json,status) VALUES(?,?,?,?,?,?,?,?)',(cid,page_url,sig,captcha,int(phone),int(no_sol),json.dumps(fields),status)); c.commit(); c.close()
                            ev=EVIDENCE/f'{cid:09d}_{d.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True)
                            (ev/'form.json').write_text(json.dumps({'domain':d,'page_url':page_url,'captcha':captcha,'phone_required':phone,'no_solicitation':no_sol,'fields':fields,'status':status},indent=2),encoding='utf-8')
                    c=conn(); c.execute('UPDATE companies SET status=? WHERE id=?',('FORM_FOUND' if found else 'NO_FORM',cid)); c.commit(); c.close()
            await asyncio.gather(*(one(r) for r in rows))

async def visual_evidence():
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        while True:
            c=conn(); rows=c.execute("SELECT f.id,c.id,c.domain,f.page_url FROM forms f JOIN companies c ON c.id=f.company_id WHERE f.status IN ('CONTACTABLE','CAPTCHA','PHONE_REQUIRED') AND NOT EXISTS(SELECT 1 FROM forms x WHERE x.id=f.id AND x.fields_json LIKE '%screenshot_done%') LIMIT 20").fetchall(); c.close()
            if not rows: await asyncio.sleep(10); continue
            for fid,cid,d,url in rows:
                ev=EVIDENCE/f'{cid:09d}_{d.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True); out=ev/'contact-page.png'
                ctx=await browser.new_context(viewport={'width':1440,'height':1100}); page=await ctx.new_page()
                try:
                    await page.goto(url,wait_until='domcontentloaded',timeout=30000); await page.wait_for_timeout(1500); await page.screenshot(path=str(out),full_page=True)
                except Exception: pass
                await ctx.close()
                c=conn(); row=c.execute('SELECT fields_json FROM forms WHERE id=?',(fid,)).fetchone(); payload=json.loads(row[0] or '[]') if row else []; payload.append({'screenshot_done':True,'path':str(out)}); c.execute('UPDATE forms SET fields_json=? WHERE id=?',(json.dumps(payload),fid)); c.commit(); c.close()

async def stats():
    while True:
        c=conn(); companies=c.execute('SELECT COUNT(*) FROM companies').fetchone()[0]; forms=c.execute('SELECT COUNT(*) FROM forms').fetchone()[0]; contactable=c.execute("SELECT COUNT(*) FROM forms WHERE status='CONTACTABLE'").fetchone()[0]; captcha=c.execute("SELECT COUNT(*) FROM forms WHERE status='CAPTCHA'").fetchone()[0]; c.close()
        print(f'STATS companies={companies} forms={forms} contactable={contactable} captcha={captcha}',flush=True); await asyncio.sleep(60)

async def main():
    init(); await asyncio.gather(discovery(),resolver(),visual_evidence(),stats())

if __name__=='__main__': asyncio.run(main())
