import asyncio, json, os
from pathlib import Path
import asyncpg, httpx
from browser_use import Agent, Browser, ChatOllama

APP=Path('/opt/exior-contact-indexer')
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
MODEL=os.getenv('BROWSER_USE_MODEL','llama3.1:8b')
BATCH_SIZE=int(os.getenv('BATCH_SIZE','3'))
CONCURRENCY=int(os.getenv('SMART_WORKERS','1'))
NAME='Guillaume Bauchart'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; PHONE='+33 7 55 71 99 59'; WEBSITE='https://exior.io/marketing-agencies/'
MESSAGE='''Hi — we built EXIOR specifically for marketing agencies.\n\nIt installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.\n\nWe handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.\n\nSee exactly what gets installed:\nhttps://exior.io/marketing-agencies/\n\n— Guillaume\nEXIOR'''
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries','no vendors','no vendor solicitations')
CAPTCHA=('recaptcha','hcaptcha','h-captcha','cf-turnstile','turnstile','captcha')

SCHEMA='''
CREATE TABLE IF NOT EXISTS browseruse_attempts_v6(
 id BIGSERIAL PRIMARY KEY,
 company_id BIGINT UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
 form_url TEXT,
 started_at TIMESTAMPTZ DEFAULT now(),
 finished_at TIMESTAMPTZ,
 status TEXT,
 result_text TEXT,
 result_json JSONB DEFAULT '{}'::jsonb
);
'''

class Gate:
 def __init__(self,n): self.n=n; self.claimed=0; self.lock=asyncio.Lock()
 async def reserve(self):
  async with self.lock:
   if self.claimed>=self.n:return False
   self.claimed+=1; return True

async def init(pool):
 async with pool.acquire() as c:
  await c.execute(SCHEMA)
  await c.execute("UPDATE outreach_queue SET status='DEFERRED_PRECHECK',updated_at=now() WHERE status='SMART_RUNNING' AND updated_at < now()-interval '30 minutes'")

async def claim(pool,gate):
 if not await gate.reserve(): return None
 async with pool.acquire() as c:
  async with c.transaction():
   row=await c.fetchrow('''
    SELECT q.company_id,c.domain,q.form_url
    FROM outreach_queue q JOIN companies c ON c.id=q.company_id
    LEFT JOIN browseruse_attempts_v6 a ON a.company_id=q.company_id
    WHERE q.status='DEFERRED_PRECHECK' AND (a.company_id IS NULL OR a.status='SMART_ERROR')
    ORDER BY q.updated_at FOR UPDATE OF q SKIP LOCKED LIMIT 1
   ''')
   if row:
    await c.execute("UPDATE outreach_queue SET status='SMART_RUNNING',updated_at=now() WHERE company_id=$1",row['company_id'])
    return row
 return None

async def safest_route(pool,cid,preferred):
 async with pool.acquire() as c:
  rows=await c.fetch("SELECT page_url FROM forms WHERE company_id=$1 AND status='CONTACTABLE' ORDER BY (page_url=$2) DESC,(page_url ILIKE '%contact%') DESC,(page_url ILIKE '%get-in-touch%') DESC,id LIMIT 8",cid,preferred)
 return [x['page_url'] for x in rows]

async def preflight(url):
 try:
  async with httpx.AsyncClient(follow_redirects=True,timeout=15,headers={'User-Agent':'Mozilla/5.0'}) as c:
   r=await c.get(url); txt=r.text.lower()
   if any(x in txt for x in NO_SOLICIT): return False,'NO_SOLICITATION'
   if any(x in txt for x in CAPTCHA): return False,'CAPTCHA_BLOCKED'
   if r.status_code>=400:return False,f'HTTP_{r.status_code}'
   return True,''
 except Exception as e:return False,f'FETCH_{type(e).__name__}'

async def run_agent(url):
 llm=ChatOllama(model=MODEL)
 browser=Browser(headless=True)
 task=f'''Open exactly this company contact page: {url}\n\nGoal: send ONE legitimate B2B enquiry from EXIOR to this marketing agency.\n\nUse these truthful values where fields request them:\nName: {NAME}\nCompany: {COMPANY}\nEmail: {EMAIL}\nPhone: {PHONE}\nWebsite: {WEBSITE}\nMessage:\n{MESSAGE}\n\nRules:\n- Understand the rendered page and actual form, including unusual labels, multi-step forms, selects and embedded frames.\n- Choose neutral business/general/new-project options when a required dropdown asks for enquiry type.\n- Never invent personal or company facts beyond the values above.\n- Never bypass CAPTCHA, anti-bot protections, login, or access controls.\n- If the page explicitly says no sales, no vendors, no solicitation, or the form is only for support/jobs/press, STOP without submitting.\n- Submit AT MOST ONCE. After clicking final submit once, do not retry.\n- Return exactly one prefix: SUCCESS_CONFIRMED, SUBMIT_ATTEMPTED, or NOT_SUBMITTED, then a concise reason.\n'''
 agent=Agent(task=task,llm=llm,browser=browser,max_actions_per_step=5,max_failures=2)
 try:
  hist=await asyncio.wait_for(agent.run(max_steps=18),timeout=180)
  try: return hist.final_result() or ''
  except Exception: return str(hist)
 finally:
  try: await browser.stop()
  except Exception: pass

async def save(pool,row,url,status,text,details):
 async with pool.acquire() as c:
  await c.execute('''INSERT INTO browseruse_attempts_v6(company_id,form_url,status,result_text,result_json,finished_at) VALUES($1,$2,$3,$4,$5::jsonb,now()) ON CONFLICT(company_id) DO UPDATE SET form_url=EXCLUDED.form_url,status=EXCLUDED.status,result_text=EXCLUDED.result_text,result_json=EXCLUDED.result_json,finished_at=now()''',row['company_id'],url,status,text,json.dumps(details))
  await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",status,row['company_id'])

async def worker(pool,gate,n):
 while True:
  if gate.claimed>=gate.n:return
  row=await claim(pool,gate)
  if not row:
   if gate.claimed>=gate.n:return
   await asyncio.sleep(1); continue
  routes=await safest_route(pool,row['company_id'],row['form_url'])
  chosen=None; rejected=[]
  for url in routes:
   ok,reason=await preflight(url)
   if ok: chosen=url; break
   rejected.append({'url':url,'reason':reason})
  if not chosen:
   await save(pool,row,row['form_url'],'SMART_NO_SAFE_ROUTE','',{'rejected':rejected}); continue
  try:
   text=await run_agent(chosen); upper=text.upper()
   if upper.startswith('SUCCESS_CONFIRMED'): status='SUCCESS_CONFIRMED'
   elif upper.startswith('SUBMIT_ATTEMPTED'): status='SUBMIT_ATTEMPTED'
   else: status='SMART_NOT_SUBMITTED'
   await save(pool,row,chosen,status,text,{'model':MODEL,'route':chosen,'rejected':rejected})
  except Exception as e:
   await save(pool,row,chosen,'SMART_ERROR','',{'error':f'{type(e).__name__}:{str(e)[:1000]}','model':MODEL})

async def main():
 pool=await asyncpg.create_pool(PG_DSN,min_size=2,max_size=max(6,CONCURRENCY+3)); await init(pool); gate=Gate(BATCH_SIZE)
 await asyncio.gather(*[asyncio.create_task(worker(pool,gate,i)) for i in range(CONCURRENCY)])
 async with pool.acquire() as c:
  rows=await c.fetch("SELECT status,count(*) n FROM browseruse_attempts_v6 GROUP BY status ORDER BY n DESC")
  deferred=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='DEFERRED_PRECHECK'")
 print('V6_SMART_DONE',gate.claimed,'deferred_remaining=',deferred,'results=',[(r['status'],r['n']) for r in rows],flush=True)
 await pool.close()

if __name__=='__main__': asyncio.run(main())