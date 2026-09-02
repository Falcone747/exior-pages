import asyncio,json,os,re,time
from pathlib import Path
import asyncpg
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer'); EVIDENCE=APP/'evidence'
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
SEND_WORKERS=int(os.getenv('SEND_WORKERS','8')); BATCH_SIZE=int(os.getenv('BATCH_SIZE','100'))
NAME='Guillaume'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; WEBSITE='https://exior.io/marketing-agencies/'; SUBJECT='EXIOR for marketing agencies'
MESSAGE="""Hi — we built EXIOR specifically for marketing agencies.\n\nIt installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.\n\nWe handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.\n\nSee exactly what gets installed:\nhttps://exior.io/marketing-agencies/\n\n— Guillaume\nEXIOR"""
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries','no vendors','no vendor solicitations')
TOPIC_ONLY=('careers only','jobs only','press enquiries only','press inquiries only','support only','customer support only','technical support only')
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')
SUCCESS_WORDS=('thank you','thanks for contacting','thanks for reaching out','message sent','message has been sent','successfully submitted','submission received',"we'll be in touch",'we will be in touch','thanks for your message','thank you for your message','we have received your message','your enquiry has been received','your inquiry has been received')
SCHEMA='''CREATE TABLE IF NOT EXISTS submissions_v3(id BIGSERIAL PRIMARY KEY,company_id BIGINT UNIQUE REFERENCES companies(id) ON DELETE CASCADE,form_id BIGINT REFERENCES forms(id),form_url TEXT,attempted_at TIMESTAMPTZ DEFAULT now(),status TEXT,confirmation TEXT,before_png TEXT,filled_png TEXT,after_png TEXT,result_json JSONB DEFAULT '{}'::jsonb); CREATE INDEX IF NOT EXISTS submissions_v3_status_idx ON submissions_v3(status);'''

class Gate:
 def __init__(self,n): self.limit=n; self.claimed=0; self.lock=asyncio.Lock()
 async def reserve(self):
  async with self.lock:
   if self.claimed>=self.limit:return False
   self.claimed+=1;return True
 async def rollback(self):
  async with self.lock:self.claimed=max(0,self.claimed-1)

async def init(pool):
 async with pool.acquire() as c:
  await c.execute(SCHEMA)
  await c.execute("UPDATE outreach_queue SET status='MESSAGE_READY',updated_at=now() WHERE status='SENDING' AND updated_at<now()-interval '20 minutes'")

async def claim(pool,gate):
 if not await gate.reserve(): return None
 async with pool.acquire() as c:
  async with c.transaction():
   row=await c.fetchrow("""SELECT q.company_id,q.form_id,q.form_url,co.domain FROM outreach_queue q JOIN companies co ON co.id=q.company_id JOIN forms f ON f.id=q.form_id LEFT JOIN submissions_v3 s ON s.company_id=q.company_id WHERE q.status='MESSAGE_READY' AND f.status='CONTACTABLE' AND s.company_id IS NULL ORDER BY q.id FOR UPDATE OF q SKIP LOCKED LIMIT 1""")
   if row:
    await c.execute("UPDATE outreach_queue SET status='SENDING',updated_at=now() WHERE company_id=$1",row['company_id']); return row
 await gate.rollback(); return None

def semantic(f):
 t=' '.join(str(f.get(k) or '') for k in ('name','id','placeholder','aria','label','nearby')).lower(); typ=(f.get('type') or '').lower(); tag=(f.get('tag') or '').lower()
 if typ=='email' or re.search(r'\be-?mail\b',t):return 'email'
 if re.search(r'\b(phone|telephone|mobile|tel)\b',t):return 'phone'
 if re.search(r'\b(company|organisation|organization|business name|agency name)\b',t):return 'company'
 if re.search(r'\b(website|web site|company url|your site|site url)\b',t):return 'website'
 if re.search(r'\b(subject|topic|reason for contacting)\b',t):return 'subject'
 if tag=='textarea' or any(x in t for x in ('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','your needs','describe','what would you like','how may we help')):return 'message'
 if re.search(r'\b(full name|your name|name)\b',t):return 'name'
 return 'unknown'

async def fields(ctx):
 loc=ctx.locator('input:visible,textarea:visible,select:visible,[contenteditable="true"]:visible,[role="textbox"]:visible')
 return loc,await loc.evaluate_all('''els=>els.map((e,i)=>{const id=e.id||'';let label='';if(id){const l=document.querySelector(`label[for="${CSS.escape(id)}"]`);if(l)label=l.innerText||l.textContent||''}if(!label){const p=e.closest('label');if(p)label=p.innerText||p.textContent||''}const wrap=e.closest('.field,.form-field,.input-group,.form-group,.hs-form-field,.wpforms-field,[class*="field"],[class*="form"]');return {i,tag:e.tagName.toLowerCase(),name:e.name||'',id,placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',type:(e.type||'').toLowerCase(),required:!!e.required||e.getAttribute('aria-required')==='true',disabled:!!e.disabled,label,nearby:wrap?(wrap.innerText||wrap.textContent||'').slice(0,700):''}})''')

async def find_context(page):
 contexts=[page]+[f for f in page.frames if f!=page.main_frame]
 best=None
 for ctx in contexts:
  try:
   controls,fs=await fields(ctx); score=sum(5 for f in fs if semantic(f)=='message')+sum(1 for f in fs if semantic(f) in ('email','name','company','website'))
   if score and (best is None or score>best[0]):best=(score,ctx,controls,fs)
  except Exception:pass
 return best

async def fill_context(ctx,controls,fs):
 message=False
 for f in fs:
  if f['disabled'] or f['type'] in ('hidden','submit','button','file','image','reset','checkbox','radio'):continue
  kind=semantic(f); loc=controls.nth(f['i'])
  try:
   if kind=='phone' and f['required']:return False,'REQUIRED_PHONE'
   if kind=='email':await loc.fill(EMAIL,timeout=2500)
   elif kind=='company':await loc.fill(COMPANY,timeout=2500)
   elif kind=='website':await loc.fill(WEBSITE,timeout=2500)
   elif kind=='name':await loc.fill(NAME,timeout=2500)
   elif kind=='subject' and f['required']:await loc.fill(SUBJECT,timeout=2500)
   elif kind=='message':await loc.fill(MESSAGE,timeout=2500);message=True
  except Exception:pass
 if not message:
  for sel in ('textarea:visible','[contenteditable="true"]:visible','[role="textbox"]:visible'):
   x=ctx.locator(sel)
   for i in range(min(await x.count(),5)):
    try:
     el=x.nth(i); await el.fill(MESSAGE,timeout=2000); message=True; break
    except Exception:pass
   if message:break
 return message,('OK' if message else 'NO_MESSAGE_FIELD')

async def save(pool,row,status,confirmation,before,filled,after,payload):
 async with pool.acquire() as c:
  await c.execute("""INSERT INTO submissions_v3(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) ON CONFLICT(company_id) DO UPDATE SET status=EXCLUDED.status,confirmation=EXCLUDED.confirmation,before_png=EXCLUDED.before_png,filled_png=EXCLUDED.filled_png,after_png=EXCLUDED.after_png,result_json=EXCLUDED.result_json,attempted_at=now()""",row['company_id'],row['form_id'],row['form_url'],status,confirmation,str(before),str(filled),str(after),json.dumps(payload))
  await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",status,row['company_id'])

async def worker(pool,browser,gate,n):
 while True:
  if gate.claimed>=gate.limit:return
  row=await claim(pool,gate)
  if not row:
   if gate.claimed>=gate.limit:return
   await asyncio.sleep(1);continue
  cid,fid,url,domain=row['company_id'],row['form_id'],row['form_url'],row['domain']; ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}';ev.mkdir(parents=True,exist_ok=True)
  before,filled,after=ev/f'v3v2-{fid}-01-before.png',ev/f'v3v2-{fid}-02-filled.png',ev/f'v3v2-{fid}-03-after.png';status='ERROR';confirmation='';clicked=False;err=''
  ctxb=await browser.new_context(viewport={'width':1440,'height':1100});page=await ctxb.new_page()
  try:
   await page.goto(url,wait_until='domcontentloaded',timeout=30000);await page.wait_for_timeout(1200);await page.screenshot(path=str(before),full_page=True)
   html=(await page.content()).lower();body=(await page.locator('body').inner_text()).lower()
   if any(x in body for x in NO_SOLICIT):status='NO_SOLICITATION';raise RuntimeError('no_solicitation')
   if any(x in body for x in TOPIC_ONLY):status='TOPIC_ONLY';raise RuntimeError('topic_only')
   if any(x in html for x in CAPTCHA_HINTS):status='CAPTCHA_BLOCKED';raise RuntimeError('captcha')
   found=await find_context(page)
   if not found:status='NO_MESSAGE_FIELD';raise RuntimeError('no_form_context')
   _,formctx,controls,fs=found
   ok,why=await fill_context(formctx,controls,fs)
   if not ok:status=why;raise RuntimeError(why.lower())
   for f in fs:
    if f['type']!='checkbox' or not f['required']:continue
    txt=((f.get('label') or '')+' '+(f.get('nearby') or '')).lower()
    if any(x in txt for x in ('newsletter','marketing emails','promotional','subscribe')):continue
    if any(x in txt for x in ('privacy','terms','consent','agree')):
     try:await controls.nth(f['i']).check(timeout=2000)
     except Exception:pass
   await page.screenshot(path=str(filled),full_page=True)
   submit=formctx.locator('button[type="submit"]:visible,input[type="submit"]:visible')
   if await submit.count()==0:submit=formctx.get_by_role('button',name=re.compile(r'^(send|submit|contact|enquire|inquire|send message|send enquiry|send inquiry|request|continue|send request)$',re.I))
   if await submit.count()==0:
    forms=formctx.locator('form:visible')
    if await forms.count():submit=forms.first.locator('button:visible').last
   if await submit.count()==0:status='NO_SUBMIT_BUTTON';raise RuntimeError('no_submit')
   old=page.url;await submit.first.click(timeout=10000);clicked=True;await page.wait_for_timeout(5000);new=page.url
   text=(await page.locator('body').inner_text()).lower();html2=(await page.content()).lower();alerts=''
   try:alerts=(await page.locator('[role="alert"]:visible,[aria-live]:visible').all_inner_texts());alerts=' '.join(alerts).lower()
   except Exception:pass
   if any(x in text or x in alerts for x in SUCCESS_WORDS):status='SUCCESS_CONFIRMED';confirmation='explicit_confirmation'
   elif new!=old and re.search(r'thank|success|submitted|confirmation|received',new,re.I):status='SUCCESS_CONFIRMED';confirmation='confirmation_redirect'
   elif any(x in html2 for x in SUCCESS_WORDS):status='SUCCESS_CONFIRMED';confirmation='explicit_confirmation_html'
   else:status='FAILED_CONFIRMATION'
   await page.screenshot(path=str(after),full_page=True)
  except Exception as e:
   err=f'{type(e).__name__}:{str(e)[:300]}'
   if not after.exists():
    try:await page.screenshot(path=str(after),full_page=True)
    except Exception:pass
  finally:
   payload={'company_id':cid,'domain':domain,'form_url':url,'status':status,'confirmation':confirmation,'clicked_submit':clicked,'error':err,'batch_size':BATCH_SIZE,'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'screenshots':{'before':str(before),'filled':str(filled),'after':str(after)}}
   (ev/f'v3v2-{fid}-result.json').write_text(json.dumps(payload,indent=2),encoding='utf-8');await save(pool,row,status,confirmation,before,filled,after,payload);await ctxb.close()

async def main():
 EVIDENCE.mkdir(parents=True,exist_ok=True);pool=await asyncpg.create_pool(PG_DSN,min_size=4,max_size=max(20,SEND_WORKERS+8));await init(pool);gate=Gate(BATCH_SIZE)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage']);await asyncio.gather(*[asyncio.create_task(worker(pool,browser,gate,i)) for i in range(SEND_WORKERS)]);await browser.close()
 async with pool.acquire() as c:
  rows=await c.fetch('SELECT status,count(*) n FROM submissions_v3 GROUP BY status ORDER BY n DESC');ready=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY'")
 print('BATCH_DONE claimed=',gate.claimed,' ready_remaining=',ready,' results=',[(r['status'],r['n']) for r in rows],flush=True);await pool.close()
if __name__=='__main__':asyncio.run(main())
