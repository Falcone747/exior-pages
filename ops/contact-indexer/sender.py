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
 "we\'ll be in touch",'we will be in touch','thanks for your message',
 'thank you for your message'
)
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')


def conn():
    c=sqlite3.connect(DB,timeout=60,check_same_thread=False)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')
    c.execute('PRAGMA busy_timeout=60000')
    return c


def init():
    c=conn()
    c.executescript('''
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
    ''')
    c.commit(); c.close()


def semantic(f):
    t=' '.join([f.get('name',''),f.get('id',''),f.get('placeholder',''),f.get('aria','')]).lower()
    typ=f.get('type','').lower()
    if typ=='email' or 'email' in t:return 'email'
    if re.search(r'phone|telephone|mobile|tel\\b',t):return 'phone'
    if 'company' in t or 'organisation' in t or 'organization' in t or 'business name' in t:return 'company'
    if 'website' in t or 'your site' in t or 'company url' in t:return 'website'
    if 'subject' in t or 'topic' in t:return 'subject'
    if any(x in t for x in ('message','how can we help','tell us about','project','brief','inquiry','enquiry','details','comments')):return 'message'
    if 'name' in t:return 'name'
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
    if row:
        c.execute("UPDATE outreach_queue SET status='SENDING' WHERE company_id=?",(row[0],))
    c.commit(); c.close(); return row


async def save_result(cid,fid,url,status,confirmation,before,filled,after,payload):
    c=conn()
    c.execute('''
      INSERT OR REPLACE INTO submissions(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json)
      VALUES(?,?,?,?,?,?,?,?,?)
    ''',(cid,fid,url,status,confirmation,str(before),str(filled),str(after),json.dumps(payload)))
    c.execute('UPDATE outreach_queue SET status=? WHERE company_id=?',(status,cid))
    c.commit(); c.close()


async def worker(browser,n):
    while True:
        row=await claim_one()
        if not row:
            await asyncio.sleep(2)
            continue

        cid,fid,url,domain=row
        ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}'
        ev.mkdir(parents=True,exist_ok=True)
        before=ev/f'send-{fid}-01-before.png'
        filled=ev/f'send-{fid}-02-filled.png'
        after=ev/f'send-{fid}-03-after.png'
        status='ERROR'; confirmation=''

        ctx=await browser.new_context(viewport={'width':1440,'height':1100})
        page=await ctx.new_page()

        try:
            await page.goto(url,wait_until='domcontentloaded',timeout=30000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(before),full_page=True)

            html=(await page.content()).lower()
            text=(await page.locator('body').inner_text()).lower()

            if any(x in text for x in NO_SOLICIT):
                status='NO_SOLICITATION'
                raise RuntimeError('no_solicitation')

            if any(x in html for x in CAPTCHA_HINTS):
                status='CAPTCHA_BLOCKED'
                raise RuntimeError('captcha')

            fields=await page.locator('input,textarea,select').evaluate_all('''els=>els.map((e,i)=>({i,name:e.name||'',id:e.id||'',placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',type:(e.type||'').toLowerCase(),required:e.required||e.getAttribute('aria-required')==='true'}))''')

            if any(semantic(f)=='phone' and f['required'] for f in fields):
                status='REQUIRED_PHONE'
                raise RuntimeError('phone')

            message_field=False

            for f in fields:
                loc=page.locator('input,textarea,select').nth(f['i'])
                kind=semantic(f)
                try:
                    if kind=='phone':
                        continue
                    if kind=='email':
                        await loc.fill(EMAIL)
                    elif kind=='company':
                        await loc.fill(COMPANY)
                    elif kind=='website':
                        await loc.fill(WEBSITE)
                    elif kind=='name':
                        await loc.fill(NAME)
                    elif kind=='subject' and f['required']:
                        await loc.fill(SUBJECT)
                    elif kind=='message':
                        await loc.fill(MESSAGE)
                        message_field=True
                except Exception:
                    pass

            if not message_field:
                status='NO_MESSAGE_FIELD'
                raise RuntimeError('no_message_field')

            await page.screenshot(path=str(filled),full_page=True)

            submit=page.locator("button[type=submit],input[type=submit]")
            if await submit.count()==0:
                status='NO_SUBMIT_BUTTON'
                raise RuntimeError('no_submit')

            old_url=page.url
            await submit.first.click(timeout=10000)
            await page.wait_for_timeout(5000)
            new_url=page.url
            result_html=(await page.content()).lower()

            if any(x in result_html for x in SUCCESS_WORDS):
                status='SUCCESS'
                confirmation='explicit_confirmation'
            elif new_url!=old_url and re.search(r'thank|success|submitted|confirmation',new_url,re.I):
                status='SUCCESS'
                confirmation='confirmation_redirect'
            else:
                status='FAILED_CONFIRMATION'

            await page.screenshot(path=str(after),full_page=True)

        except Exception:
            if not filled.exists():
                try: await page.screenshot(path=str(filled),full_page=True)
                except Exception: pass
            if not after.exists():
                try: await page.screenshot(path=str(after),full_page=True)
                except Exception: pass

        finally:
            payload={
                'company_id':cid,
                'domain':domain,
                'form_url':url,
                'status':status,
                'confirmation':confirmation,
                'website_used':WEBSITE,
                'phone_used':False,
                'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                'screenshots':{
                    'before':str(before),
                    'filled':str(filled),
                    'after':str(after)
                }
            }
            (ev/f'send-{fid}-result.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
            await save_result(cid,fid,url,status,confirmation,before,filled,after,payload)
            await ctx.close()


async def stats():
    while True:
        c=conn()
        rows=c.execute("SELECT status,COUNT(*) FROM submissions GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
        ready=c.execute("SELECT COUNT(*) FROM outreach_queue WHERE status='MESSAGE_READY'").fetchone()[0]
        sending=c.execute("SELECT COUNT(*) FROM outreach_queue WHERE status='SENDING'").fetchone()[0]
        c.close()
        print(f'SEND_STATS ready={ready} sending={sending} results={rows}',flush=True)
        await asyncio.sleep(30)


async def main():
    init()
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        tasks=[asyncio.create_task(stats())]+[asyncio.create_task(worker(browser,i)) for i in range(SEND_WORKERS)]
        await asyncio.gather(*tasks)

if __name__=='__main__':
    asyncio.run(main())
