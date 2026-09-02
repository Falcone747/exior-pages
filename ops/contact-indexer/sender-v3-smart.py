import asyncio, json, os, re, time
from pathlib import Path
import asyncpg
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
EVIDENCE=APP/'evidence'
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
SEND_WORKERS=int(os.getenv('SEND_WORKERS','8'))
BATCH_SIZE=int(os.getenv('BATCH_SIZE','100'))
MAX_ROUTES=int(os.getenv('MAX_ROUTES','5'))

NAME='Guillaume'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; WEBSITE='https://exior.io/marketing-agencies/'
SUBJECT='EXIOR for marketing agencies'
MESSAGE="""Hi — we built EXIOR specifically for marketing agencies.

It installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.

We handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.

See exactly what gets installed:
https://exior.io/marketing-agencies/

— Guillaume
EXIOR"""

NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries','no vendors','no vendor solicitations')
TOPIC_ONLY=('careers only','jobs only','press enquiries only','press inquiries only','support only','customer support only','technical support only')
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')
SUCCESS_WORDS=('thank you','thanks for contacting','thanks for reaching out','message sent','message has been sent','successfully submitted','submission received',"we'll be in touch",'we will be in touch','thanks for your message','thank you for your message','we have received your message','your enquiry has been received','your inquiry has been received')

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

class Gate:
    def __init__(self,n): self.n=n; self.claimed=0; self.lock=asyncio.Lock()
    async def reserve(self):
        async with self.lock:
            if self.claimed>=self.n: return False
            self.claimed+=1; return True
    async def rollback(self):
        async with self.lock: self.claimed=max(0,self.claimed-1)

async def init(pool):
    async with pool.acquire() as c:
        await c.execute(SCHEMA)
        await c.execute("UPDATE outreach_queue SET status='MESSAGE_READY',updated_at=now() WHERE status='SENDING' AND updated_at < now()-interval '20 minutes'")

async def claim_company(pool,gate):
    if not await gate.reserve(): return None
    async with pool.acquire() as c:
        async with c.transaction():
            row=await c.fetchrow('''
                SELECT q.company_id,co.domain,q.form_id AS preferred_form_id,q.form_url AS preferred_url
                FROM outreach_queue q
                JOIN companies co ON co.id=q.company_id
                LEFT JOIN submissions_v3 s ON s.company_id=q.company_id
                WHERE q.status='MESSAGE_READY' AND s.company_id IS NULL
                ORDER BY q.id
                FOR UPDATE OF q SKIP LOCKED
                LIMIT 1
            ''')
            if row:
                await c.execute("UPDATE outreach_queue SET status='SENDING',updated_at=now() WHERE company_id=$1",row['company_id'])
                return row
    await gate.rollback(); return None

async def routes(pool,cid,preferred_id):
    async with pool.acquire() as c:
        return await c.fetch('''
            SELECT id,page_url
            FROM forms
            WHERE company_id=$1 AND status='CONTACTABLE'
            ORDER BY (id=$2) DESC,
                     (page_url ILIKE '%contact%') DESC,
                     (page_url ILIKE '%get-in-touch%') DESC,
                     (page_url ILIKE '%enquir%') DESC,
                     id
            LIMIT $3
        ''',cid,preferred_id,MAX_ROUTES)

def semantic(meta):
    t=' '.join(str(meta.get(k) or '') for k in ('name','id','placeholder','aria','label','title','autocomplete','nearby')).lower()
    typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower(); role=(meta.get('role') or '').lower()
    if typ=='email' or meta.get('autocomplete')=='email' or re.search(r'\be-?mail\b',t): return 'email'
    if typ=='tel' or meta.get('autocomplete')=='tel' or re.search(r'\b(phone|telephone|mobile|tel)\b',t): return 'phone'
    if re.search(r'\b(company|organisation|organization|business|agency|company name|organisation name)\b',t): return 'company'
    if re.search(r'\b(website|web site|company url|site url|domain)\b',t): return 'website'
    if re.search(r'\b(subject|topic|reason for contacting|reason for enquiry|reason for inquiry)\b',t): return 'subject'
    if tag=='textarea' or role=='textbox' and meta.get('contenteditable'):
        return 'message'
    if any(x in t for x in ('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','what can we help','your needs','describe','what do you need','project details')): return 'message'
    if meta.get('autocomplete') in ('name','given-name','family-name') or re.search(r'\b(full name|your name|first name|last name|name)\b',t): return 'name'
    return 'unknown'

async def visible_meta(scope):
    loc=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    return await loc.evaluate_all('''els=>els.map((e,i)=>{
      const id=e.id||''; let label='';
      if(id){try{const l=document.querySelector(`label[for="${CSS.escape(id)}"]`);if(l)label=l.innerText||l.textContent||'';}catch(_){}}
      if(!label){const p=e.closest('label');if(p)label=p.innerText||p.textContent||'';}
      const wrap=e.closest('.field,.form-field,.input-group,.form-group,.hs-form-field,.wpforms-field,[class*="field"],[class*="form"]');
      return {i,tag:e.tagName.toLowerCase(),name:e.name||'',id,placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',title:e.title||'',autocomplete:e.autocomplete||'',role:e.getAttribute('role')||'',contenteditable:e.isContentEditable,type:(e.type||'').toLowerCase(),required:!!e.required||e.getAttribute('aria-required')==='true',label,nearby:wrap?(wrap.innerText||wrap.textContent||'').slice(0,700):''};
    })''')

async def score_scope(scope):
    try:
        metas=await visible_meta(scope)
    except Exception:
        return -999,[],None
    kinds=[semantic(m) for m in metas]
    score=0
    if 'message' in kinds: score+=12
    if 'email' in kinds: score+=5
    if 'name' in kinds: score+=3
    if 'company' in kinds: score+=2
    if 'subject' in kinds: score+=1
    if any(k=='phone' and m.get('required') for k,m in zip(kinds,metas)): score-=30
    try:
        submits=scope.locator('button[type="submit"]:visible,input[type="submit"]:visible,button:visible')
        if await submits.count(): score+=3
    except Exception: pass
    return score,metas,kinds

async def best_form(page):
    candidates=[]
    for frame in page.frames:
        try:
            forms=frame.locator('form:visible')
            n=min(await forms.count(),12)
            for i in range(n):
                scope=forms.nth(i)
                score,metas,kinds=await score_scope(scope)
                candidates.append((score,frame,scope,metas,kinds,f'form[{i}]'))
            # Some embedded/custom forms have no <form> wrapper.
            score,metas,kinds=await score_scope(frame)
            if score>=12:
                candidates.append((score-1,frame,frame,metas,kinds,'frame-root'))
        except Exception:
            continue
    if not candidates: return None
    candidates.sort(key=lambda x:x[0],reverse=True)
    return candidates[0]

async def fill_scope(scope,metas,kinds):
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    message_ok=False; required_unknown=[]
    for m,k in zip(metas,kinds):
        loc=controls.nth(m['i'])
        typ=m.get('type','')
        if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
        try:
            if k=='email': await loc.fill(EMAIL)
            elif k=='company': await loc.fill(COMPANY)
            elif k=='website': await loc.fill(WEBSITE)
            elif k=='name': await loc.fill(NAME)
            elif k=='subject': await loc.fill(SUBJECT)
            elif k=='message': await loc.fill(MESSAGE); message_ok=True
            elif m.get('required') and (m.get('tag')!='select'): required_unknown.append(m)
        except Exception:
            if m.get('required'): required_unknown.append(m)
    # Required consent checkboxes only; never opt into marketing/newsletters.
    checks=scope.locator('input[type="checkbox"]:visible')
    for i in range(await checks.count()):
        loc=checks.nth(i)
        try:
            req=await loc.get_attribute('required') is not None or (await loc.get_attribute('aria-required'))=='true'
            if not req: continue
            txt=((await loc.get_attribute('aria-label')) or '')+' '+((await loc.get_attribute('name')) or '')
            txt=txt.lower()
            if any(x in txt for x in ('newsletter','marketing','promotional','subscribe')): continue
            await loc.check()
        except Exception: pass
    return message_ok,required_unknown

async def find_submit(scope):
    direct=scope.locator('button[type="submit"]:visible,input[type="submit"]:visible')
    if await direct.count(): return direct.first
    buttons=scope.locator('button:visible')
    n=await buttons.count()
    rx=re.compile(r'^(send|submit|contact|enquire|inquire|send message|send enquiry|send inquiry|request|send request|get in touch|contact us)$',re.I)
    for i in range(n):
        b=buttons.nth(i)
        try:
            text=(await b.inner_text()).strip()
            if rx.search(text): return b
        except Exception: pass
    return None

async def attempt_route(browser,cid,domain,fid,url):
    ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True)
    before=ev/f'smart-{fid}-01-before.png'; filled=ev/f'smart-{fid}-02-filled.png'; after=ev/f'smart-{fid}-03-after.png'
    ctx=await browser.new_context(viewport={'width':1440,'height':1100}); page=await ctx.new_page()
    result={'form_id':fid,'url':url,'clicked':False,'status':'PRECHECK_FAILED','reason':'unknown','before':str(before),'filled':str(filled),'after':str(after)}
    try:
        await page.goto(url,wait_until='domcontentloaded',timeout=30000); await page.wait_for_timeout(1600)
        await page.screenshot(path=str(before),full_page=True)
        html=(await page.content()).lower(); body=(await page.locator('body').inner_text()).lower()
        if any(x in body for x in NO_SOLICIT): result.update(status='NO_SOLICITATION',reason='live_no_solicitation'); return result
        if any(x in body for x in TOPIC_ONLY): result.update(status='TOPIC_ONLY',reason='live_topic_only'); return result
        if any(x in html for x in CAPTCHA_HINTS): result.update(status='CAPTCHA_BLOCKED',reason='live_captcha'); return result
        best=await best_form(page)
        if not best: result.update(status='NO_USABLE_FORM',reason='no_form_scope'); return result
        score,frame,scope,metas,kinds,scope_name=best
        result['form_score']=score; result['scope']=scope_name; result['kinds']=kinds
        if score<12 or 'message' not in kinds:
            result.update(status='NO_MESSAGE_FIELD',reason=f'best_score={score}'); return result
        if any(k=='phone' and m.get('required') for k,m in zip(kinds,metas)):
            result.update(status='REQUIRED_PHONE',reason='required_phone_live'); return result
        message_ok,required_unknown=await fill_scope(scope,metas,kinds)
        result['required_unknown']=[{k:v for k,v in m.items() if k in ('name','id','placeholder','label','type')} for m in required_unknown[:8]]
        if not message_ok:
            result.update(status='NO_MESSAGE_FIELD',reason='message_fill_failed'); return result
        submit=await find_submit(scope)
        if submit is None:
            result.update(status='NO_SUBMIT_BUTTON',reason='no_form_local_submit'); return result
        # If there are required unknown text fields, do not guess values or submit malformed data.
        if required_unknown:
            result.update(status='REQUIRED_UNKNOWN',reason='unmapped_required_fields'); return result
        await page.screenshot(path=str(filled),full_page=True)
        old_url=page.url
        await submit.click(timeout=10000); result['clicked']=True
        await page.wait_for_timeout(5000)
        text=(await page.locator('body').inner_text()).lower(); html2=(await page.content()).lower(); new_url=page.url
        if any(x in text for x in SUCCESS_WORDS): result.update(status='SUCCESS_CONFIRMED',reason='explicit_confirmation')
        elif new_url!=old_url and re.search(r'thank|success|submitted|confirmation|received',new_url,re.I): result.update(status='SUCCESS_CONFIRMED',reason='confirmation_redirect')
        elif any(x in html2 for x in SUCCESS_WORDS): result.update(status='SUCCESS_CONFIRMED',reason='explicit_confirmation_html')
        else: result.update(status='FAILED_CONFIRMATION',reason='clicked_no_confirmation')
        try: await page.screenshot(path=str(after),full_page=True)
        except Exception: pass
        return result
    except Exception as e:
        result.update(status='ERROR',reason=f'{type(e).__name__}:{str(e)[:300]}')
        try: await page.screenshot(path=str(after),full_page=True)
        except Exception: pass
        return result
    finally:
        await ctx.close()

async def save(pool,row,final,attempts):
    chosen=next((a for a in attempts if a.get('clicked')),attempts[-1] if attempts else {})
    async with pool.acquire() as c:
        await c.execute('''INSERT INTO submissions_v3(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            ON CONFLICT(company_id) DO UPDATE SET form_id=EXCLUDED.form_id,form_url=EXCLUDED.form_url,status=EXCLUDED.status,confirmation=EXCLUDED.confirmation,before_png=EXCLUDED.before_png,filled_png=EXCLUDED.filled_png,after_png=EXCLUDED.after_png,result_json=EXCLUDED.result_json''',
            row['company_id'],chosen.get('form_id'),chosen.get('url'),final,chosen.get('reason',''),chosen.get('before'),chosen.get('filled'),chosen.get('after'),json.dumps({'domain':row['domain'],'attempts':attempts,'batch_size':BATCH_SIZE,'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}))
        await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",final,row['company_id'])

async def worker(pool,browser,gate,n):
    while True:
        if gate.claimed>=gate.n: return
        row=await claim_company(pool,gate)
        if not row:
            if gate.claimed>=gate.n: return
            await asyncio.sleep(1); continue
        rs=await routes(pool,row['company_id'],row['preferred_form_id'])
        attempts=[]; final='NO_USABLE_FORM'
        for r in rs:
            a=await attempt_route(browser,row['company_id'],row['domain'],r['id'],r['page_url']); attempts.append(a)
            if a['status']=='SUCCESS_CONFIRMED': final='SUCCESS_CONFIRMED'; break
            if a.get('clicked'):
                # Never risk a duplicate submission after any final click.
                final=a['status']; break
            final=a['status']
        await save(pool,row,final,attempts)
        print(f"SMART_RESULT worker={n} domain={row['domain']} final={final} routes={len(attempts)}",flush=True)

async def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    pool=await asyncpg.create_pool(PG_DSN,min_size=4,max_size=max(24,SEND_WORKERS+10)); await init(pool); gate=Gate(BATCH_SIZE)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        await asyncio.gather(*[asyncio.create_task(worker(pool,browser,gate,i)) for i in range(SEND_WORKERS)])
        await browser.close()
    async with pool.acquire() as c:
        rows=await c.fetch("SELECT status,count(*) n FROM submissions_v3 GROUP BY status ORDER BY n DESC")
        ready=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY'")
    print('SMART_BATCH_DONE claimed=',gate.claimed,' ready_remaining=',ready,' results=',[(r['status'],r['n']) for r in rows],flush=True)
    await pool.close()

if __name__=='__main__': asyncio.run(main())
