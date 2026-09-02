import asyncio, json, os, re, sqlite3, time
from pathlib import Path

from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
DB=APP/'data'/'index.db'
EVIDENCE=APP/'evidence'
SEND_WORKERS=int(os.getenv('SEND_WORKERS','4'))

NAME='Guillaume'
COMPANY='EXIOR'
EMAIL='contact@exior.io'
WEBSITE='https://exior.io/marketing-agencies/'
SUBJECT='EXIOR for marketing agencies'

MESSAGE="""Hi — we built EXIOR specifically for marketing agencies.

It installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.

We handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.

See exactly what gets installed:
https://exior.io/marketing-agencies/

— Guillaume
EXIOR"""

NO_SOLICIT=(
 'no solicitation','no solicitations','no unsolicited','do not use this form for sales',
 'no sales enquiries','no sales inquiries','no vendors','no vendor solicitations'
)
SUCCESS_WORDS=(
 'thank you','thanks for contacting','thanks for reaching out','message sent',
 'message has been sent','successfully submitted','submission received',
 "we'll be in touch",'we will be in touch','thanks for your message',
 'thank you for your message','we have received your message','your enquiry has been received',
 'your inquiry has been received'
)
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')


def conn():
    c=sqlite3.connect(DB,timeout=60,check_same_thread=False)
    c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=NORMAL'); c.execute('PRAGMA busy_timeout=60000')
    return c


def init():
    c=conn(); c.executescript('''
    CREATE TABLE IF NOT EXISTS submissions(
      id INTEGER PRIMARY KEY,
      company_id INTEGER UNIQUE,
      form_id INTEGER,
      form_url TEXT,
      attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
      status TEXT,
      confirmation TEXT,
      before_png TEXT,
      filled_png TEXT,
      after_png TEXT,
      result_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
    '''); c.commit(); c.close()


def semantic(f):
    t=' '.join([
        f.get('name',''),f.get('id',''),f.get('placeholder',''),f.get('aria',''),
        f.get('label',''),f.get('nearby','')
    ]).lower()
    typ=f.get('type','').lower(); tag=f.get('tag','').lower()
    if typ=='email' or re.search(r'\be-?mail\b',t): return 'email'
    if re.search(r'\b(phone|telephone|mobile|tel)\b',t): return 'phone'
    if re.search(r'\b(company|organisation|organization|business name|agency name)\b',t): return 'company'
    if re.search(r'\b(website|web site|company url|your site|site url)\b',t): return 'website'
    if re.search(r'\b(subject|topic|reason for contacting)\b',t): return 'subject'
    if tag=='textarea': return 'message'
    if any(x in t for x in ('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','what can we help','your needs','describe')): return 'message'
    if re.search(r'\b(full name|your name|name)\b',t): return 'name'
    return 'unknown'


async def claim_one():
    c=conn(); c.execute('BEGIN IMMEDIATE')
    row=c.execute('''
      SELECT q.company_id,q.form_id,q.form_url,c.domain
      FROM outreach_queue q
      JOIN companies c ON c.id=q.company_id
      LEFT JOIN submissions s ON s.company_id=q.company_id
      WHERE q.status='MESSAGE_READY' AND s.company_id IS NULL
      LIMIT 1
    ''').fetchone()
    if row: c.execute("UPDATE outreach_queue SET status='SENDING' WHERE company_id=?",(row[0],))
    c.commit(); c.close(); return row


async def save_result(cid,fid,url,status,confirmation,before,filled,after,payload):
    c=conn(); c.execute('''
      INSERT OR REPLACE INTO submissions(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json)
      VALUES(?,?,?,?,?,?,?,?,?)
    ''',(cid,fid,url,status,confirmation,str(before),str(filled),str(after),json.dumps(payload)))
    c.execute('UPDATE outreach_queue SET status=? WHERE company_id=?',(status,cid)); c.commit(); c.close()


async def collect_fields(page):
    return await page.locator('input,textarea,select,[contenteditable="true"]').evaluate_all('''els=>els.map((e,i)=>{
      const id=e.id||'';
      let label='';
      if(id){const l=document.querySelector(`label[for="${CSS.escape(id)}"]`); if(l) label=l.innerText||l.textContent||'';}
      if(!label){const p=e.closest('label'); if(p) label=p.innerText||p.textContent||'';}
      const wrap=e.closest('.field,.form-field,.input-group,.form-group,.hs-form-field,.wpforms-field,[class*="field"],[class*="form"]');
      const nearby=wrap ? (wrap.innerText||wrap.textContent||'').slice(0,500) : '';
      return {i,tag:e.tagName.toLowerCase(),name:e.name||'',id,placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',type:(e.type||'').toLowerCase(),required:!!e.required||e.getAttribute('aria-required')==='true',label,nearby};
    })''')


async def fill_field(locator,kind,required):
    if kind=='phone': return False
    if kind=='email': await locator.fill(EMAIL); return True
    if kind=='company': await locator.fill(COMPANY); return True
    if kind=='website': await locator.fill(WEBSITE); return True
    if kind=='name': await locator.fill(NAME); return True
    if kind=='subject' and required: await locator.fill(SUBJECT); return True
    if kind=='message': await locator.fill(MESSAGE); return True
    return False


async def worker(browser,n):
    while True:
        row=await claim_one()
        if not row:
            await asyncio.sleep(2); continue
        cid,fid,url,domain=row
        ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}'
        ev.mkdir(parents=True,exist_ok=True)
        before=ev/f'send-{fid}-01-before.png'; filled=ev/f'send-{fid}-02-filled.png'; after=ev/f'send-{fid}-03-after.png'
        status='ERROR'; confirmation=''; clicked=False
        ctx=await browser.new_context(viewport={'width':1440,'height':1100})
        page=await ctx.new_page()
        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000)
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(before),full_page=True)
            html=(await page.content()).lower(); body=(await page.locator('body').inner_text()).lower()
            if any(x in body for x in NO_SOLICIT): status='NO_SOLICITATION'; raise RuntimeError('no_solicitation')
            if any(x in html for x in CAPTCHA_HINTS): status='CAPTCHA_BLOCKED'; raise RuntimeError('captcha')

            fields=await collect_fields(page)
            if any(semantic(f)=='phone' and f['required'] for f in fields): status='REQUIRED_PHONE'; raise RuntimeError('phone')

            controls=page.locator('input,textarea,select,[contenteditable="true"]')
            message_field=False
            for f in fields:
                kind=semantic(f); loc=controls.nth(f['i'])
                try:
                    if f['type'] in ('hidden','submit','button','file','image','reset'): continue
                    if f['type'] in ('checkbox','radio'): continue
                    changed=await fill_field(loc,kind,f['required'])
                    if changed and kind=='message': message_field=True
                except Exception: pass

            # Fallback: first visible textarea or contenteditable is almost always the free-text message field.
            if not message_field:
                for sel in ('textarea:visible','[contenteditable="true"]:visible'):
                    loc=page.locator(sel)
                    if await loc.count():
                        try:
                            await loc.first.fill(MESSAGE); message_field=True; break
                        except Exception: pass
            if not message_field: status='NO_MESSAGE_FIELD'; raise RuntimeError('no_message_field')

            # Required non-marketing consent checkboxes only.
            for f in fields:
                if f['type']!='checkbox' or not f['required']: continue
                text=(f.get('label','')+' '+f.get('nearby','')).lower()
                if any(x in text for x in ('newsletter','marketing emails','promotional','subscribe')): continue
                if any(x in text for x in ('privacy','terms','consent','agree')):
                    try: await controls.nth(f['i']).check()
                    except Exception: pass

            await page.screenshot(path=str(filled),full_page=True)

            submit=page.locator('button[type="submit"]:visible,input[type="submit"]:visible')
            if await submit.count()==0:
                submit=page.get_by_role('button',name=re.compile(r'^(send|submit|contact|enquire|inquire|send message|send enquiry|send inquiry|request|continue)$',re.I))
            if await submit.count()==0:
                # Last safe fallback: visible button inside the nearest form.
                forms=page.locator('form:visible')
                if await forms.count(): submit=forms.first.locator('button:visible').last
            if await submit.count()==0: status='NO_SUBMIT_BUTTON'; raise RuntimeError('no_submit')

            old_url=page.url
            await submit.first.click(timeout=10000); clicked=True
            await page.wait_for_timeout(6000)
            new_url=page.url; result_html=(await page.content()).lower(); result_text=(await page.locator('body').inner_text()).lower()
            if any(x in result_text for x in SUCCESS_WORDS): status='SUCCESS'; confirmation='explicit_confirmation'
            elif new_url!=old_url and re.search(r'thank|success|submitted|confirmation|received',new_url,re.I): status='SUCCESS'; confirmation='confirmation_redirect'
            elif any(x in result_html for x in SUCCESS_WORDS): status='SUCCESS'; confirmation='explicit_confirmation_html'
            else: status='FAILED_CONFIRMATION'
            await page.screenshot(path=str(after),full_page=True)
        except Exception:
            if not after.exists():
                try: await page.screenshot(path=str(after),full_page=True)
                except Exception: pass
        finally:
            payload={'company_id':cid,'domain':domain,'form_url':url,'status':status,'confirmation':confirmation,'clicked_submit':clicked,'website_used':WEBSITE,'phone_used':False,'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'screenshots':{'before':str(before),'filled':str(filled),'after':str(after)}}
            (ev/f'send-{fid}-result.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
            await save_result(cid,fid,url,status,confirmation,before,filled,after,payload)
            await ctx.close()


async def stats():
    while True:
        c=conn(); rows=c.execute("SELECT status,COUNT(*) FROM submissions GROUP BY status ORDER BY COUNT(*) DESC").fetchall(); c.close()
        print('SEND_STATS',rows,flush=True); await asyncio.sleep(30)


async def main():
    init()
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        tasks=[asyncio.create_task(stats())]+[asyncio.create_task(worker(browser,i)) for i in range(SEND_WORKERS)]
        await asyncio.gather(*tasks)

if __name__=='__main__': asyncio.run(main())
