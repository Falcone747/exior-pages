import asyncio, hashlib, json, os, random, sqlite3, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import geonamescache, httpx, tldextract
from bs4 import BeautifulSoup
from ddgs import DDGS
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
DB=APP/'data'/'index.db'
EVIDENCE=APP/'evidence'
COUNTRIES={'US':'United States','GB':'United Kingdom','CA':'Canada','AU':'Australia','IE':'Ireland','NZ':'New Zealand'}
TERMS=['marketing agency','digital marketing agency','advertising agency','seo agency','ppc agency','performance marketing agency','social media agency','creative agency','branding agency','growth marketing agency','content marketing agency','media agency','web marketing agency']
CONTACT_HINTS=('contact','get-in-touch','get in touch','enquire','inquire','inquiry','enquiry','talk-to-us','talk to us','quote','request-a-quote','brief','start-a-project')
PHONE_HINTS=('phone','telephone','mobile','tel')
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries')
HTTP_CONCURRENCY=int(os.getenv('HTTP_CONCURRENCY','120'))
DISCOVERY_WORKERS=int(os.getenv('DISCOVERY_WORKERS','12'))
SCREENSHOT_WORKERS=int(os.getenv('SCREENSHOT_WORKERS','8'))
CITY_MIN_POP=int(os.getenv('CITY_MIN_POP','25000'))

MESSAGE="""Hi — we built EXIOR specifically for marketing agencies.

It installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.

We handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.

See exactly what gets installed:
https://exior.io/marketing-agencies/

— Guillaume
EXIOR"""

SHORT_MESSAGE="""Hi — we built EXIOR for marketing agencies: a private intelligence and execution layer that identifies what to sell, improve and automate, then helps implement the highest-value systems. Initial installation: US$500, first working system within 72h.

https://exior.io/marketing-agencies/

— Guillaume, EXIOR"""

def conn():
    c=sqlite3.connect(DB,timeout=60,check_same_thread=False)
    c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=NORMAL'); c.execute('PRAGMA busy_timeout=60000')
    return c

def init():
    APP.mkdir(parents=True,exist_ok=True); (APP/'data').mkdir(exist_ok=True); EVIDENCE.mkdir(exist_ok=True)
    c=conn(); c.executescript('''
    CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY,domain TEXT UNIQUE,homepage TEXT,country TEXT,source_url TEXT,discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,status TEXT DEFAULT 'DISCOVERED');
    CREATE TABLE IF NOT EXISTS forms(id INTEGER PRIMARY KEY,company_id INTEGER,page_url TEXT,signature TEXT,captcha TEXT,phone_required INTEGER,no_solicitation INTEGER,fields_json TEXT,status TEXT,UNIQUE(company_id,page_url,signature));
    CREATE TABLE IF NOT EXISTS outreach_queue(id INTEGER PRIMARY KEY,company_id INTEGER UNIQUE,form_id INTEGER,form_url TEXT,message TEXT,short_message TEXT,website TEXT DEFAULT 'https://exior.io/marketing-agencies/',status TEXT DEFAULT 'MESSAGE_READY',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
    CREATE INDEX IF NOT EXISTS idx_forms_status ON forms(status);
    CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_queue(status);
    '''); c.commit(); c.close()

def domain(url):
    try:
        x=tldextract.extract(url); return f'{x.domain}.{x.suffix}'.lower() if x.domain and x.suffix else None
    except Exception:return None

def add_company(d,country,source):
    if not d:return
    c=conn(); c.execute('INSERT OR IGNORE INTO companies(domain,homepage,country,source_url) VALUES(?,?,?,?)',(d,'https://'+d+'/',country,source)); c.commit(); c.close()

def cities():
    gc=geonamescache.GeonamesCache(); out={x:[] for x in COUNTRIES}
    for row in gc.get_cities().values():
        cc=row.get('countrycode'); pop=int(row.get('population') or 0)
        if cc in out and pop>=CITY_MIN_POP: out[cc].append((pop,row['name']))
    return {cc:[n for _,n in sorted(v,reverse=True)] for cc,v in out.items()}

async def query_producer(q):
    cm=cities()
    while True:
        jobs=[(cc,country,city,term) for cc,country in COUNTRIES.items() for city in cm[cc] for term in TERMS]
        random.shuffle(jobs)
        for job in jobs: await q.put(job)
        await asyncio.sleep(900)

async def discovery_worker(q,n):
    while True:
        cc,country,city,term=await q.get(); query=f'"{term}" "{city}"'
        try:
            rows=await asyncio.to_thread(lambda:list(DDGS().text(query,max_results=30)))
            for r in rows:
                u=r.get('href') or r.get('url') or ''; add_company(domain(u),country,u)
        except Exception as e:
            print(f'DISCOVERY_ERROR worker={n} query={query!r} err={e!r}',flush=True)
        finally:
            q.task_done(); await asyncio.sleep(random.uniform(.35,.9))

async def fetch(client,url):
    try:
        r=await client.get(url,follow_redirects=True,timeout=15,headers={'User-Agent':'Mozilla/5.0 (compatible; EXIORContactIndexer/2.0)'})
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
    return [u for u,_ in sorted(scored.items(),key=lambda x:x[1],reverse=True)[:10]]

def inspect(html):
    low=html.lower(); captcha='none'
    if 'turnstile' in low: captcha='turnstile'
    elif 'hcaptcha' in low or 'h-captcha' in low: captcha='hcaptcha'
    elif 'recaptcha' in low: captcha='recaptcha'
    elif 'captcha' in low: captcha='other'
    no_sol=any(x in low for x in NO_SOLICIT); soup=BeautifulSoup(html,'lxml'); forms=[]
    for f in soup.find_all('form'):
        raw=str(f); sig=hashlib.sha1(raw.encode(errors='ignore')).hexdigest()[:20]; fields=[]; phone=False
        for e in f.find_all(['input','textarea','select']):
            label=' '.join([e.get('name',''),e.get('id',''),e.get('placeholder',''),e.get('aria-label','')]); req=e.has_attr('required') or e.get('aria-required')=='true'
            fields.append({'tag':e.name,'type':e.get('type',''),'label':label,'required':req})
            if req and any(x in label.lower() for x in PHONE_HINTS): phone=True
        forms.append((sig,fields,phone))
    return captcha,no_sol,forms

async def claim_companies(limit=200):
    c=conn(); c.execute('BEGIN IMMEDIATE')
    rows=c.execute("SELECT id,domain,homepage FROM companies WHERE status='DISCOVERED' LIMIT ?",(limit,)).fetchall()
    if rows: c.executemany("UPDATE companies SET status='RESOLVING' WHERE id=?",[(r[0],) for r in rows])
    c.commit(); c.close(); return rows

async def resolver_worker(client,sem,n):
    while True:
        rows=await claim_companies(80)
        if not rows: await asyncio.sleep(2); continue
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
                c=conn(); c.execute('UPDATE companies SET status=? WHERE id=?',('FORM_FOUND' if found else 'NO_FORM',cid)); c.commit(); c.close()
        await asyncio.gather(*(one(r) for r in rows))

async def screenshot_worker(browser,n):
    while True:
        c=conn(); row=c.execute("SELECT f.id,c.id,c.domain,f.page_url,f.fields_json FROM forms f JOIN companies c ON c.id=f.company_id WHERE f.status IN ('CONTACTABLE','CAPTCHA','PHONE_REQUIRED') AND f.fields_json NOT LIKE '%\"screenshot_done\"%' LIMIT 1").fetchone(); c.close()
        if not row: await asyncio.sleep(2); continue
        fid,cid,d,url,fields_json=row
        ev=EVIDENCE/f'{cid:09d}_{d.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True); out=ev/f'form-{fid}.png'
        ctx=await browser.new_context(viewport={'width':1440,'height':1100}); page=await ctx.new_page()
        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000); await page.wait_for_timeout(1200); await page.screenshot(path=str(out),full_page=True)
        except Exception: pass
        await ctx.close()
        try: payload=json.loads(fields_json or '[]')
        except Exception: payload=[]
        payload.append({'screenshot_done':True,'path':str(out),'ts':int(time.time())})
        c=conn(); c.execute('UPDATE forms SET fields_json=? WHERE id=?',(json.dumps(payload),fid)); c.commit(); c.close()

async def message_preparer():
    while True:
        c=conn(); rows=c.execute("SELECT c.id,f.id,f.page_url FROM companies c JOIN forms f ON f.company_id=c.id LEFT JOIN outreach_queue q ON q.company_id=c.id WHERE f.status='CONTACTABLE' AND q.company_id IS NULL GROUP BY c.id LIMIT 500").fetchall()
        if rows:
            c.executemany("INSERT OR IGNORE INTO outreach_queue(company_id,form_id,form_url,message,short_message) VALUES(?,?,?,?,?)",[(cid,fid,url,MESSAGE,SHORT_MESSAGE) for cid,fid,url in rows]); c.commit()
        c.close(); await asyncio.sleep(2)

async def stats():
    while True:
        c=conn(); companies=c.execute('SELECT COUNT(*) FROM companies').fetchone()[0]; forms=c.execute('SELECT COUNT(*) FROM forms').fetchone()[0]; ready=c.execute("SELECT COUNT(DISTINCT company_id) FROM outreach_queue WHERE status='MESSAGE_READY'").fetchone()[0]; resolving=c.execute("SELECT COUNT(*) FROM companies WHERE status='RESOLVING'").fetchone()[0]; captcha=c.execute("SELECT COUNT(*) FROM forms WHERE status='CAPTCHA'").fetchone()[0]; c.close()
        print(f'STATS companies={companies} forms={forms} message_ready_companies={ready} resolving={resolving} captcha={captcha}',flush=True); await asyncio.sleep(30)

async def main():
    init(); q=asyncio.Queue(maxsize=5000); sem=asyncio.Semaphore(HTTP_CONCURRENCY)
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=HTTP_CONCURRENCY+20,max_keepalive_connections=HTTP_CONCURRENCY)) as client:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            tasks=[asyncio.create_task(query_producer(q)),asyncio.create_task(message_preparer()),asyncio.create_task(stats())]
            tasks += [asyncio.create_task(discovery_worker(q,i)) for i in range(DISCOVERY_WORKERS)]
            tasks += [asyncio.create_task(resolver_worker(client,sem,i)) for i in range(max(4,DISCOVERY_WORKERS//2))]
            tasks += [asyncio.create_task(screenshot_worker(browser,i)) for i in range(SCREENSHOT_WORKERS)]
            await asyncio.gather(*tasks)

if __name__=='__main__': asyncio.run(main())
