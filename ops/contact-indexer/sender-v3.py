import asyncio, json, os, re, time
from pathlib import Path
import asyncpg
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
EVIDENCE=APP/'evidence'
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
SEND_WORKERS=int(os.getenv('SEND_WORKERS','4'))
MAX_PER_HOUR=int(os.getenv('MAX_PER_HOUR','120'))
NAME='Guillaume'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; WEBSITE='https://exior.io/marketing-agencies/'; SUBJECT='EXIOR for marketing agencies'
MESSAGE="""Hi — we built EXIOR specifically for marketing agencies.

It installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.

We handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.

See exactly what gets installed:
https://exior.io/marketing-agencies/

— Guillaume
EXIOR"""
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries','no vendors','no vendor solicitations')
SUCCESS_WORDS=('thank you','thanks for contacting','thanks for reaching out','message sent','message has been sent','successfully submitted','submission received',"we\'ll be in touch",'we will be in touch','thanks for your message','thank you for your message','we have received your message','your enquiry has been received','your inquiry has been received')
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')
TOPIC_ONLY=('careers only','jobs only','press enquiries only','press inquiries only','support only','customer support only','technical support only')
SCHEMA='''
CREATE TABLE IF NOT EXISTS submissions_v3(
 id BIGSERIAL PRIMARY KEY,
 company_id BIGINT UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
 form_id BIGINT REFERENCES forms(id),
 form_url TEXT,
 attempted_at TIMESTAMPTZ DEFAULT now(),
 status TEXT,
 confirmation TEXT,
 before_png TEXT,
 filled_png TEXT,
 after_png TEXT,
 result_json JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS submissions_v3_status_idx ON submissions_v3(status);
'''

async def init(pool):
    async with pool.acquire() as c:
        await c.execute(SCHEMA)
        await c.execute("UPDATE outreach_queue SET status='MESSAGE_READY',updated_at=now() WHERE status='SENDING' AND updated_at < now()-interval '15 minutes'")

def semantic(f):
    vals=[f.get('name'),f.get('id'),f.get('placeholder'),f.get('aria'),f.get('label'),f.get('nearby')]
    t=' '.join((x or '') for x in vals).lower(); typ=(f.get('type') or '').lower(); tag=(f.get('tag') or '').lower()
    if typ=='email' or re.search(r'\be-?mail\b',t): return 'email'
    if re.search(r'\b(phone|telephone|mobile|tel)\b',t): return 'phone'
    if re.search(r'\b(company|organisation|organization|business name|agency name)\b',t): return 'company'
    if re.search(r'\b(website|web site|company url|your site|site url)\b',t): return 'website'
    if re.search(r'\b(subject|topic|reason for contacting)\b',t): return 'subject'
    if tag=='textarea' or any(x in t for x in ('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','what can we help','your needs','describe')): return 'message'
    if re.search(r'\b(full name|your name|name)\b',t): return 'name'
    return 'unknown'

async def collect_fields(page):
    return await page.locator('input,textarea,select,[contenteditable="true"]').evaluate_all('''els=>els.map((e,i)=>{const id=e.id||'';let label='';if(id){const l=document.querySelector(`label[for="${CSS.escape(id)}"]`);if(l)label=l.innerText||l.textContent||'';}if(!label){const p=e.closest('label');if(p)label=p.innerText||p.textContent||'';}const wrap=e.closest('.field,.form-field,.input-group,.form-group,.hs-form-field,.wpforms-field,[class*="field"],[class*="form"]');const nearby=wrap?(wrap.innerText||wrap.textContent||'').slice(0,500):'';return {i,tag:e.tagName.toLowerCase(),name:e.name||'',id,placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',type:(e.type||'').toLowerCase(),required:!!e.required||e.getAttribute('aria-required')==='true',label,nearby};})''')

async def claim_one(pool):
    async with pool.acquire() as c:
        async with c.transaction():
            # global cadence guard
            n=await c.fetchval("SELECT count(*) FROM submissions_v3 WHERE attempted_at > now()-interval '1 hour'")
            if n >= MAX_PER_HOUR: return None
            row=await c.fetchrow('''SELECT q.company_id,q.form_id,q.form_url,co.domain FROM outreach_queue q JOIN companies co ON co.id=q.company_id JOIN forms f ON f.id=q.form_id LEFT JOIN submissions_v3 s ON s.company_id=q.company_id WHERE q.status='MESSAGE_READY' AND f.status='CONTACTABLE' AND s.company_id IS NULL ORDER BY q.id FOR UPDATE OF q SKIP LOCKED LIMIT 1''')
            if row: await c.execute("UPDATE outreach_queue SET status='SENDING',updated_at=now() WHERE company_id=$1",row['company_id'])
            return row

async def save_result(pool,row,status,confirmation,before,filled,after,payload):
    async with pool.acquire() as c:
        await c.execute('''INSERT INTO submissions_v3(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) ON CONFLICT(company_id) DO UPDATE SET status=EXCLUDED.status,confirmation=EXCLUDED.confirmation,before_png=EXCLUDED.before_png,filled_png=EXCLUDED.filled_png,after_png=EXCLUDED.after_png,result_json=EXCLUDED.result_json''',row['company_id'],row['form_id'],row['form_url'],status,confirmation,str(before),str(filled),str(after),json.dumps(payload))
        await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",status,row['company_id'])

async def worker(pool,browser,n):
    while True:
        row=await claim_one(pool)
        if not row:
            await asyncio.sleep(5); continue
        cid=row['company_id']; fid=row['form_id']; url=row['form_url']; domain=row['domain']
        ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True)
        before=ev/f'v3-send-{fid}-01-before.png'; filled=ev/f'v3-send-{fid}-02-filled.png'; after=ev/f'v3-send-{fid}-03-after.png'
        status='ERROR'; confirmation=''; clicked=False
        ctx=await browser.new_context(viewport={'width':1440,'height':1100}); page=await ctx.new_page()
        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000); await page.wait_for_timeout(1800); await page.screenshot(path=str(before),full_page=True)
            html=(await page.content()).lower(); body=(await page.locator('body').inner_text()).lower()
            if any(x in body for x in NO_SOLICIT): status='NO_SOLICITATION'; raise RuntimeError('no_solicitation')
            if any(x in body for x in TOPIC_ONLY): status='TOPIC_ONLY'; raise RuntimeError('topic_only')
            if any(x in html for x in CAPTCHA_HINTS): status='CAPTCHA_BLOCKED'; raise RuntimeError('captcha')
            fields=await collect_fields(page)
            if any(semantic(f)=='phone' and f['required'] for f in fields): status='REQUIRED_PHONE'; raise RuntimeError('phone')
            controls=page.locator('input,textarea,select,[contenteditable="true"]'); message_field=False
            for f in fields:
                kind=semantic(f); loc=controls.nth(f['i'])
                try:
                    if f['type'] in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
                    if kind=='email': await loc.fill(EMAIL)
                    elif kind=='company': await loc.fill(COMPANY)
                    elif kind=='website': await loc.fill(WEBSITE)
                    elif kind=='name': await loc.fill(NAME)
                    elif kind=='subject' and f['required']: await loc.fill(SUBJECT)
                    elif kind=='message': await loc.fill(MESSAGE); message_field=True
                except Exception: pass
            if not message_field:
                ta=page.locator('textarea:visible,[contenteditable="true"]:visible')
                if await ta.count():
                    try: await ta.first.fill(MESSAGE); message_field=True
                    except Exception: pass
            if not message_field: status='NO_MESSAGE_FIELD'; raise RuntimeError('no_message_field')
            for f in fields:
                if f['type']!='checkbox' or not f['required']: continue
                text=((f.get('label') or '')+' '+(f.get('nearby') or '')).lower()
                if any(x in text for x in ('newsletter','marketing emails','promotional','subscribe')): continue
                if any(x in text for x in ('privacy','terms','consent','agree')):
                    try: await controls.nth(f['i']).check()
                    except Exception: pass
            await page.screenshot(path=str(filled),full_page=True)
            submit=page.locator('button[type="submit"]:visible,input[type="submit"]:visible')
            if await submit.count()==0: submit=page.get_by_role('button',name=re.compile(r'^(send|submit|contact|enquire|inquire|send message|send enquiry|send inquiry|request|continue)$',re.I))
            if await submit.count()==0:
                forms=page.locator('form:visible')
                if await forms.count(): submit=forms.first.locator('button:visible').last
            if await submit.count()==0: status='NO_SUBMIT_BUTTON'; raise RuntimeError('no_submit')
            old_url=page.url; await submit.first.click(timeout=10000); clicked=True; await page.wait_for_timeout(5500)
            new_url=page.url; text=(await page.locator('body').inner_text()).lower(); html2=(await page.content()).lower()
            if any(x in text for x in SUCCESS_WORDS): status='SUCCESS_CONFIRMED'; confirmation='explicit_confirmation'
            elif new_url!=old_url and re.search(r'thank|success|submitted|confirmation|received',new_url,re.I): status='SUCCESS_CONFIRMED'; confirmation='confirmation_redirect'
            elif any(x in html2 for x in SUCCESS_WORDS): status='SUCCESS_CONFIRMED'; confirmation='explicit_confirmation_html'
            else: status='FAILED_CONFIRMATION'
            await page.screenshot(path=str(after),full_page=True)
        except Exception:
            if not after.exists():
                try: await page.screenshot(path=str(after),full_page=True)
                except Exception: pass
        finally:
            payload={'company_id':cid,'domain':domain,'form_url':url,'status':status,'confirmation':confirmation,'clicked_submit':clicked,'website_used':WEBSITE,'phone_used':False,'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'screenshots':{'before':str(before),'filled':str(filled),'after':str(after)}}
            (ev/f'v3-send-{fid}-result.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
            await save_result(pool,row,status,confirmation,before,filled,after,payload); await ctx.close()

async def stats(pool):
    while True:
        async with pool.acquire() as c:
            rows=await c.fetch("SELECT status,count(*) n FROM submissions_v3 GROUP BY status ORDER BY n DESC")
            ready=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY'")
        print('V3_SEND_STATS ready=',ready,' results=',[(r['status'],r['n']) for r in rows],flush=True); await asyncio.sleep(30)

async def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True); pool=await asyncpg.create_pool(PG_DSN,min_size=4,max_size=20); await init(pool)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        tasks=[asyncio.create_task(stats(pool))]+[asyncio.create_task(worker(pool,browser,i)) for i in range(SEND_WORKERS)]
        await asyncio.gather(*tasks)

if __name__=='__main__': asyncio.run(main())
