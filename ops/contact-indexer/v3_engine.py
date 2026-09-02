import asyncio, hashlib, os, random, re, sqlite3, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import asyncpg, httpx, orjson, redis.asyncio as redis
import tldextract, uvloop
from ddgs import DDGS
from geonamescache import GeonamesCache
from rapidfuzz import fuzz
from selectolax.parser import HTMLParser
from playwright.async_api import async_playwright

uvloop.install()
APP=Path('/opt/exior-contact-indexer')
EVIDENCE=APP/'evidence'
OLD_DB=APP/'data'/'index.db'
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
REDIS_URL=os.getenv('REDIS_URL','redis://127.0.0.1:6379/0')
HTTP_CONCURRENCY=int(os.getenv('HTTP_CONCURRENCY','200'))
DISCOVERY_WORKERS=int(os.getenv('DISCOVERY_WORKERS','20'))
RESOLVER_WORKERS=int(os.getenv('RESOLVER_WORKERS','12'))
SCREENSHOT_WORKERS=int(os.getenv('SCREENSHOT_WORKERS','6'))
CITY_MIN_POP=int(os.getenv('CITY_MIN_POP','25000'))

COUNTRIES={'US':'United States','GB':'United Kingdom','CA':'Canada','AU':'Australia','IE':'Ireland','NZ':'New Zealand'}
TERMS=['marketing agency','digital marketing agency','advertising agency','seo agency','ppc agency','performance marketing agency','social media agency','creative agency','branding agency','growth marketing agency','content marketing agency','media agency','web marketing agency']
CONTACT_HINTS=('contact','get-in-touch','get in touch','enquire','inquire','inquiry','enquiry','talk-to-us','talk to us','quote','request-a-quote','brief','start-a-project','start a project','work-with-us','work with us')
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries')
PHONE_HINTS=('phone','telephone','mobile','tel')

MESSAGE='''Hi — we built EXIOR specifically for marketing agencies.\n\nIt installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.\n\nWe handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.\n\nSee exactly what gets installed:\nhttps://exior.io/marketing-agencies/\n\n— Guillaume\nEXIOR'''
SHORT_MESSAGE='''Hi — we built EXIOR for marketing agencies: a private intelligence and execution layer that identifies what to sell, improve and automate, then helps implement the highest-value systems. Initial installation: US$500, first working system within 72h.\n\nhttps://exior.io/marketing-agencies/\n\n— Guillaume, EXIOR'''

SCHEMA='''
CREATE TABLE IF NOT EXISTS companies(
 id BIGSERIAL PRIMARY KEY, domain TEXT UNIQUE NOT NULL, homepage TEXT, country TEXT, source_url TEXT,
 discovered_at TIMESTAMPTZ DEFAULT now(), status TEXT DEFAULT 'DISCOVERED', updated_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS companies_status_idx ON companies(status);
CREATE TABLE IF NOT EXISTS forms(
 id BIGSERIAL PRIMARY KEY, company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
 page_url TEXT NOT NULL, signature TEXT NOT NULL, captcha TEXT DEFAULT 'none', phone_required BOOLEAN DEFAULT false,
 no_solicitation BOOLEAN DEFAULT false, fields_json JSONB DEFAULT '[]'::jsonb, status TEXT DEFAULT 'CONTACTABLE',
 screenshot_path TEXT, screenshot_done BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT now(),
 UNIQUE(company_id,page_url,signature));
CREATE INDEX IF NOT EXISTS forms_status_idx ON forms(status);
CREATE INDEX IF NOT EXISTS forms_screenshot_idx ON forms(screenshot_done);
CREATE TABLE IF NOT EXISTS outreach_queue(
 id BIGSERIAL PRIMARY KEY, company_id BIGINT UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
 form_id BIGINT REFERENCES forms(id), form_url TEXT, message TEXT, short_message TEXT,
 website TEXT DEFAULT 'https://exior.io/marketing-agencies/', status TEXT DEFAULT 'MESSAGE_READY',
 created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS outreach_status_idx ON outreach_queue(status);
'''

def canonical_domain(url):
    try:
        x=tldextract.extract(url)
        return f'{x.domain}.{x.suffix}'.lower() if x.domain and x.suffix else None
    except Exception:return None

def cities():
    gc=GeonamesCache(); out={x:[] for x in COUNTRIES}
    for row in gc.get_cities().values():
        cc=row.get('countrycode'); pop=int(row.get('population') or 0)
        if cc in out and pop>=CITY_MIN_POP: out[cc].append((pop,row['name']))
    return {cc:[n for _,n in sorted(v,reverse=True)] for cc,v in out.items()}

async def setup(pool):
    async with pool.acquire() as c: await c.execute(SCHEMA)
    if OLD_DB.exists(): await migrate_old(pool)

async def migrate_old(pool):
    marker=APP/'data'/'.sqlite_migrated_v3'
    if marker.exists(): return
    try:
        s=sqlite3.connect(OLD_DB)
        rows=s.execute('SELECT domain,homepage,country,source_url,status FROM companies').fetchall()
        async with pool.acquire() as c:
            await c.executemany('''INSERT INTO companies(domain,homepage,country,source_url,status) VALUES($1,$2,$3,$4,$5)
             ON CONFLICT(domain) DO NOTHING''', rows)
        s.close(); marker.write_text(str(len(rows)))
        print('MIGRATED_SQLITE',len(rows),flush=True)
    except Exception as e: print('MIGRATION_ERROR',repr(e),flush=True)

async def add_company(pool,d,country,source):
    if not d:return
    async with pool.acquire() as c:
        await c.execute('''INSERT INTO companies(domain,homepage,country,source_url) VALUES($1,$2,$3,$4)
         ON CONFLICT(domain) DO NOTHING''',d,'https://'+d+'/',country,source)

async def query_producer(r):
    cm=cities(); jobs=[(cc,country,city,term) for cc,country in COUNTRIES.items() for city in cm[cc] for term in TERMS]
    while True:
        random.shuffle(jobs)
        pipe=r.pipeline()
        for cc,country,city,term in jobs:
            await pipe.rpush('q:search',orjson.dumps([cc,country,city,term]))
            if len(pipe.command_stack)>=500:
                await pipe.execute(); pipe=r.pipeline()
        if pipe.command_stack: await pipe.execute()
        await asyncio.sleep(1800)

async def discovery_worker(pool,r,n):
    while True:
        item=await r.blpop('q:search',timeout=5)
        if not item: continue
        cc,country,city,term=orjson.loads(item[1]); q=f'"{term}" "{city}"'
        try:
            rows=await asyncio.to_thread(lambda:list(DDGS().text(q,max_results=30)))
            for x in rows:
                u=x.get('href') or x.get('url') or ''
                await add_company(pool,canonical_domain(u),country,u)
        except Exception as e:
            print(f'DISCOVERY_ERROR worker={n} {type(e).__name__}',flush=True)
            await asyncio.sleep(random.uniform(.5,1.5))

async def fetch(client,url):
    try:
        r=await client.get(url,follow_redirects=True,timeout=12,headers={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36'})
        if r.status_code<400 and 'html' in r.headers.get('content-type',''): return str(r.url),r.text
    except Exception:pass
    return None,None

def candidate_links(base,html):
    tree=HTMLParser(html); host=urlparse(base).netloc; scored={}
    for a in tree.css('a'):
        href=a.attributes.get('href') or ''
        if not href: continue
        u=urljoin(base,href)
        if urlparse(u).netloc!=host:continue
        text=(a.text(separator=' ',strip=True) or '').lower(); hay=(u+' '+text).lower()
        score=sum(4 for x in CONTACT_HINTS if x in u.lower())+sum(3 for x in CONTACT_HINTS if x.replace('-',' ') in text)
        if score:scored[u]=max(scored.get(u,0),score)
    for p in ['/contact','/contact-us','/get-in-touch','/enquire','/inquiry','/enquiry','/request-a-quote','/start-a-project']:
        scored.setdefault(urljoin(base,p),1)
    return [u for u,_ in sorted(scored.items(),key=lambda z:z[1],reverse=True)[:10]]

def inspect_forms(html):
    low=html.lower(); captcha='none'
    if 'turnstile' in low:captcha='turnstile'
    elif 'hcaptcha' in low or 'h-captcha' in low:captcha='hcaptcha'
    elif 'recaptcha' in low:captcha='recaptcha'
    elif 'captcha' in low:captcha='other'
    no_sol=any(x in low for x in NO_SOLICIT); tree=HTMLParser(html); out=[]
    for f in tree.css('form'):
        raw=f.html or ''; sig=hashlib.sha1(raw.encode(errors='ignore')).hexdigest()[:20]; fields=[]; phone=False
        for e in f.css('input,textarea,select'):
            attrs=e.attributes; label=' '.join([attrs.get('name',''),attrs.get('id',''),attrs.get('placeholder',''),attrs.get('aria-label','')])
            req='required' in attrs or attrs.get('aria-required')=='true'
            fields.append({'tag':e.tag,'type':attrs.get('type',''),'label':label,'required':req})
            if req and any(x in label.lower() for x in PHONE_HINTS): phone=True
        out.append((sig,fields,phone))
    return captcha,no_sol,out

async def claim_company(pool):
    async with pool.acquire() as c:
        async with c.transaction():
            row=await c.fetchrow('''SELECT id,domain,homepage FROM companies WHERE status='DISCOVERED'
             ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1''')
            if row: await c.execute("UPDATE companies SET status='RESOLVING',updated_at=now() WHERE id=$1",row['id'])
            return row

async def resolver_worker(pool,client,n):
    while True:
        row=await claim_company(pool)
        if not row: await asyncio.sleep(.3); continue
        cid,d,home=row['id'],row['domain'],row['homepage']; base,html=await fetch(client,home)
        if not html:
            async with pool.acquire() as c: await c.execute("UPDATE companies SET status='FETCH_FAILED',updated_at=now() WHERE id=$1",cid)
            continue
        found=0
        for u in candidate_links(base,html):
            page_url,page_html=await fetch(client,u)
            if not page_html:continue
            captcha,no_sol,forms=inspect_forms(page_html)
            for sig,fields,phone in forms:
                found+=1
                status='CONTACTABLE' if captcha=='none' and not phone and not no_sol else ('CAPTCHA' if captcha!='none' else 'PHONE_REQUIRED' if phone else 'NO_SOLICITATION')
                async with pool.acquire() as c:
                    await c.execute('''INSERT INTO forms(company_id,page_url,signature,captcha,phone_required,no_solicitation,fields_json,status)
                     VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT(company_id,page_url,signature) DO NOTHING''',cid,page_url,sig,captcha,phone,no_sol,orjson.loads(orjson.dumps(fields)),status)
        async with pool.acquire() as c: await c.execute("UPDATE companies SET status=$1,updated_at=now() WHERE id=$2",'FORM_FOUND' if found else 'NO_FORM',cid)

async def message_preparer(pool):
    while True:
        async with pool.acquire() as c:
            rows=await c.fetch('''SELECT DISTINCT ON (f.company_id) f.company_id,f.id,f.page_url FROM forms f
             LEFT JOIN outreach_queue q ON q.company_id=f.company_id
             WHERE f.status='CONTACTABLE' AND q.company_id IS NULL ORDER BY f.company_id,f.id LIMIT 1000''')
            if rows:
                await c.executemany('''INSERT INTO outreach_queue(company_id,form_id,form_url,message,short_message)
                 VALUES($1,$2,$3,$4,$5) ON CONFLICT(company_id) DO NOTHING''',[(x['company_id'],x['id'],x['page_url'],MESSAGE,SHORT_MESSAGE) for x in rows])
        await asyncio.sleep(1)

async def claim_screenshot(pool):
    async with pool.acquire() as c:
        async with c.transaction():
            row=await c.fetchrow('''SELECT f.id,f.company_id,f.page_url,c.domain FROM forms f JOIN companies c ON c.id=f.company_id
             WHERE f.screenshot_done=false AND f.status IN ('CONTACTABLE','CAPTCHA','PHONE_REQUIRED')
             ORDER BY f.id FOR UPDATE SKIP LOCKED LIMIT 1''')
            if row: await c.execute('UPDATE forms SET screenshot_done=true WHERE id=$1',row['id'])
            return row

async def screenshot_worker(pool,browser,n):
    while True:
        row=await claim_screenshot(pool)
        if not row: await asyncio.sleep(.5); continue
        ev=EVIDENCE/f"{row['company_id']:09d}_{row['domain'].replace('.','_')}"; ev.mkdir(parents=True,exist_ok=True)
        path=ev/f"form-{row['id']}.png"; ctx=await browser.new_context(viewport={'width':1365,'height':900}); page=await ctx.new_page()
        try:
            await page.goto(row['page_url'],wait_until='domcontentloaded',timeout=25000); await page.wait_for_timeout(800); await page.screenshot(path=str(path),full_page=True)
            async with pool.acquire() as c: await c.execute('UPDATE forms SET screenshot_path=$1 WHERE id=$2',str(path),row['id'])
        except Exception:pass
        finally: await ctx.close()

async def stats(pool):
    while True:
        async with pool.acquire() as c:
            row=await c.fetchrow('''SELECT
             (SELECT count(*) FROM companies) companies,
             (SELECT count(*) FROM companies WHERE status='RESOLVING') resolving,
             (SELECT count(*) FROM forms) forms,
             (SELECT count(*) FROM forms WHERE status='CONTACTABLE') contactable,
             (SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY') ready''')
        print('V3_STATS',dict(row),flush=True); await asyncio.sleep(30)

async def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    pool=await asyncpg.create_pool(PG_DSN,min_size=8,max_size=40,command_timeout=30)
    r=redis.from_url(REDIS_URL,decode_responses=False)
    await setup(pool)
    limits=httpx.Limits(max_connections=HTTP_CONCURRENCY,max_keepalive_connections=HTTP_CONCURRENCY)
    async with httpx.AsyncClient(limits=limits,http2=True) as client:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            tasks=[asyncio.create_task(query_producer(r)),asyncio.create_task(message_preparer(pool)),asyncio.create_task(stats(pool))]
            tasks += [asyncio.create_task(discovery_worker(pool,r,i)) for i in range(DISCOVERY_WORKERS)]
            tasks += [asyncio.create_task(resolver_worker(pool,client,i)) for i in range(RESOLVER_WORKERS)]
            tasks += [asyncio.create_task(screenshot_worker(pool,browser,i)) for i in range(SCREENSHOT_WORKERS)]
            await asyncio.gather(*tasks)

if __name__=='__main__': asyncio.run(main())
