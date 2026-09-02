import asyncio, json, os, re, time, hashlib
from pathlib import Path
from urllib.parse import urlparse

import asyncpg, httpx, orjson
from rapidfuzz import fuzz
from selectolax.lexbor import LexborHTMLParser
from playwright.async_api import async_playwright

APP=Path('/opt/exior-contact-indexer')
EVIDENCE=APP/'evidence'
PG_DSN=os.getenv('PG_DSN','postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact')
SEND_WORKERS=int(os.getenv('SEND_WORKERS','8'))
BATCH_SIZE=int(os.getenv('BATCH_SIZE','100'))
MAX_ROUTES=int(os.getenv('MAX_ROUTES','8'))
ENABLE_LOCAL_AI=os.getenv('ENABLE_LOCAL_AI','0')=='1'
OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434')
OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','qwen3:4b')

NAME='Guillaume'
FIRST_NAME='Guillaume'
LAST_NAME='Bauchart'
COMPANY='EXIOR'
EMAIL='contact@exior.io'
PHONE='+33 7 55 71 99 59'
WEBSITE='https://exior.io/marketing-agencies/'
SUBJECT='EXIOR for marketing agencies'
MESSAGE='''Hi — we built EXIOR specifically for marketing agencies.\n\nIt installs a private intelligence and execution layer across your agency: revenue opportunities, clients, delivery, capacity, margins, market/competitor intelligence, AI tools, automations and internal systems — all continuously prioritized around what creates the most value.\n\nWe handle the strategy, tool selection and implementation. The initial installation is US$500, with the first working system delivered within 72 hours.\n\nSee exactly what gets installed:\nhttps://exior.io/marketing-agencies/\n\n— Guillaume\nEXIOR'''

NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries','no vendors','no vendor solicitations')
TOPIC_ONLY=('careers only','jobs only','press enquiries only','press inquiries only','support only','customer support only','technical support only')
CAPTCHA_HINTS=('recaptcha','g-recaptcha','hcaptcha','h-captcha','turnstile','cf-turnstile','captcha')
SUCCESS_WORDS=('thank you','thanks for contacting','thanks for reaching out','message sent','message has been sent','successfully submitted','submission received',"we'll be in touch",'we will be in touch','thanks for your message','thank you for your message','we have received your message','your enquiry has been received','your inquiry has been received')
VALIDATION_WORDS=('required field','please enter','please complete','is required','invalid email','invalid phone','please select')
GENERIC_SELECT_GOOD=('general','business','sales','new business','project','other','enquiry','inquiry','partnership','marketing')
GENERIC_SELECT_BAD=('job','career','support','press','media','investor','billing')

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
CREATE TABLE IF NOT EXISTS form_recipes_v4(
 fingerprint TEXT PRIMARY KEY,
 vendor TEXT,
 recipe_json JSONB NOT NULL,
 successes INTEGER DEFAULT 0,
 failures INTEGER DEFAULT 0,
 updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sender_prechecks_v4(
 id BIGSERIAL PRIMARY KEY,
 company_id BIGINT,
 form_id BIGINT,
 form_url TEXT,
 status TEXT,
 reason TEXT,
 details JSONB DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ DEFAULT now()
);
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

async def get_routes(pool,cid,preferred_id):
    async with pool.acquire() as c:
        return await c.fetch('''
            SELECT id,page_url
            FROM forms
            WHERE company_id=$1 AND status='CONTACTABLE'
            ORDER BY (id=$2) DESC,
                     (page_url ILIKE '%contact%') DESC,
                     (page_url ILIKE '%get-in-touch%') DESC,
                     (page_url ILIKE '%enquir%') DESC,
                     (page_url ILIKE '%project%') DESC,
                     id
            LIMIT $3
        ''',cid,preferred_id,MAX_ROUTES)

async def static_probe(client,url):
    try:
        r=await client.get(url,follow_redirects=True,timeout=httpx.Timeout(12.0,connect=5.0),headers={'User-Agent':'Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36'})
        if r.status_code>=400 or 'html' not in r.headers.get('content-type',''): return {'ok':False,'reason':f'http_{r.status_code}'}
        html=r.text; low=html.lower(); tree=LexborHTMLParser(html)
        vendor='generic'
        sigs=(('hubspot','hs-form|hubspot'),('wpforms','wpforms'),('gravity','gform_|gravityforms'),('cf7','wpcf7|contact-form-7'),('webflow','w-form|webflow'),('jotform','jotform'),('typeform','typeform'),('formidable','frm_form'),('elementor','elementor-form'))
        for name,pat in sigs:
            if re.search(pat,low): vendor=name; break
        forms=tree.css('form')
        fp_src=vendor+'|'+urlparse(str(r.url)).netloc+'|'+str(len(forms))+'|'+','.join(sorted(set(x.attributes.get('name','') for f in forms for x in f.css('input,textarea,select') if x.attributes.get('name'))))
        fp=hashlib.sha1(fp_src.encode()).hexdigest()[:24]
        return {'ok':True,'vendor':vendor,'fingerprint':fp,'url':str(r.url),'form_count':len(forms)}
    except Exception as e:
        return {'ok':False,'reason':f'{type(e).__name__}:{str(e)[:120]}'}

def normtxt(meta):
    return ' '.join(str(meta.get(k) or '') for k in ('name','id','placeholder','aria','label','title','autocomplete','nearby')).strip().lower()

def semantic(meta):
    t=normtxt(meta); typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower(); role=(meta.get('role') or '').lower(); ac=(meta.get('autocomplete') or '').lower()
    if typ=='email' or ac=='email' or re.search(r'\be-?mail\b',t): return 'email'
    if typ=='tel' or ac=='tel' or re.search(r'\b(phone|telephone|mobile|tel)\b',t): return 'phone'
    if ac=='given-name' or re.search(r'\b(first name|given name|forename)\b',t): return 'first_name'
    if ac=='family-name' or re.search(r'\b(last name|surname|family name)\b',t): return 'last_name'
    if ac=='name' or re.search(r'\b(full name|your name|contact name)\b',t): return 'name'
    if re.search(r'\b(company|organisation|organization|business|agency|company name|organisation name)\b',t): return 'company'
    if re.search(r'\b(website|web site|company url|site url|domain)\b',t): return 'website'
    if re.search(r'\b(subject|topic|reason for contacting|reason for enquiry|reason for inquiry)\b',t): return 'subject'
    if tag=='textarea' or (role=='textbox' and meta.get('contenteditable')): return 'message'
    needles=('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','what can we help','your needs','describe','what do you need','project details','how may we help','how can i help','anything else','additional information')
    if any(x in t for x in needles): return 'message'
    return 'unknown'

async def ai_classify_unknown(client,meta):
    if not ENABLE_LOCAL_AI: return 'unknown'
    prompt='Classify this web form field into one token only: email, phone, first_name, last_name, name, company, website, subject, message, unknown. Field metadata: '+json.dumps(meta,ensure_ascii=False)
    try:
        r=await client.post(OLLAMA_URL.rstrip('/')+'/api/chat',json={'model':OLLAMA_MODEL,'stream':False,'messages':[{'role':'user','content':prompt}]},timeout=8)
        x=r.json().get('message',{}).get('content','').strip().lower()
        return x if x in {'email','phone','first_name','last_name','name','company','website','subject','message','unknown'} else 'unknown'
    except Exception:
        return 'unknown'

async def visible_meta(scope):
    loc=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    return await loc.evaluate_all('''els=>els.map((e,i)=>{const id=e.id||'';let label='';if(id){try{const l=document.querySelector(`label[for="${CSS.escape(id)}"]`);if(l)label=l.innerText||l.textContent||'';}catch(_){}}if(!label){const p=e.closest('label');if(p)label=p.innerText||p.textContent||'';}const wrap=e.closest('.field,.form-field,.input-group,.form-group,.hs-form-field,.wpforms-field,[class*="field"],[class*="form"],[class*="input"]');return {i,tag:e.tagName.toLowerCase(),name:e.name||'',id,placeholder:e.placeholder||'',aria:e.getAttribute('aria-label')||'',title:e.title||'',autocomplete:e.autocomplete||'',role:e.getAttribute('role')||'',contenteditable:e.isContentEditable,type:(e.type||'').toLowerCase(),required:!!e.required||e.getAttribute('aria-required')==='true',label,nearby:wrap?(wrap.innerText||wrap.textContent||'').slice(0,900):''};})''')

async def score_scope(scope):
    try: metas=await visible_meta(scope)
    except Exception: return -999,[],[]
    kinds=[semantic(m) for m in metas]
    score=0
    score += 20 if 'message' in kinds else 0
    score += 7 if 'email' in kinds else 0
    score += 4 if any(x in kinds for x in ('name','first_name','last_name')) else 0
    score += 3 if 'company' in kinds else 0
    score += 2 if 'phone' in kinds else 0
    try:
        if await scope.locator('button[type="submit"]:visible,input[type="submit"]:visible').count(): score+=5
        elif await scope.locator('button:visible').count(): score+=2
    except Exception: pass
    return score,metas,kinds

async def best_form(page):
    cand=[]
    for frame in page.frames:
        try:
            forms=frame.locator('form:visible'); n=min(await forms.count(),16)
            for i in range(n):
                s=forms.nth(i); sc,m,k=await score_scope(s); cand.append((sc,frame,s,m,k,f'form[{i}]'))
            sc,m,k=await score_scope(frame)
            if sc>=20: cand.append((sc-2,frame,frame,m,k,'frame-root'))
        except Exception: continue
    if not cand:return None
    cand.sort(key=lambda x:x[0],reverse=True); return cand[0]

async def choose_select(loc):
    try:
        opts=await loc.locator('option').all_text_contents()
        values=await loc.locator('option').evaluate_all("els=>els.map(e=>e.value)")
        best=None; bestscore=-999
        for i,(txt,val) in enumerate(zip(opts,values)):
            s=(txt or '').strip().lower()
            if not val or not s or 'select' in s or 'choose' in s: continue
            score=max([fuzz.partial_ratio(s,x) for x in GENERIC_SELECT_GOOD]+[0])-max([fuzz.partial_ratio(s,x) for x in GENERIC_SELECT_BAD]+[0])
            if score>bestscore: best=(val,txt); bestscore=score
        if best and bestscore>=20:
            await loc.select_option(value=best[0]); return True,best[1]
    except Exception: pass
    return False,None

async def fill_scope(scope,metas,kinds,ai_client):
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    message_ok=False; unresolved=[]; filled=[]
    for idx,(m,k) in enumerate(zip(metas,kinds)):
        loc=controls.nth(m['i']); typ=m.get('type',''); tag=m.get('tag','')
        if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
        if k=='unknown' and m.get('required'): k=await ai_classify_unknown(ai_client,m)
        try:
            if tag=='select':
                if m.get('required'):
                    ok,v=await choose_select(loc)
                    if ok: filled.append(('select',v))
                    else: unresolved.append(m)
                continue
            val=None
            if k=='email': val=EMAIL
            elif k=='phone': val=PHONE
            elif k=='first_name': val=FIRST_NAME
            elif k=='last_name': val=LAST_NAME
            elif k=='name': val=NAME
            elif k=='company': val=COMPANY
            elif k=='website': val=WEBSITE
            elif k=='subject': val=SUBJECT
            elif k=='message': val=MESSAGE; message_ok=True
            if val is not None:
                await loc.fill(val); filled.append((k,val[:80] if isinstance(val,str) else val))
            elif m.get('required'): unresolved.append(m)
        except Exception:
            if m.get('required'): unresolved.append(m)
    checks=scope.locator('input[type="checkbox"]:visible')
    for i in range(await checks.count()):
        loc=checks.nth(i)
        try:
            req=await loc.get_attribute('required') is not None or (await loc.get_attribute('aria-required'))=='true'
            if not req: continue
            txt=' '.join(filter(None,[(await loc.get_attribute('aria-label')),(await loc.get_attribute('name'))])).lower()
            if any(x in txt for x in ('newsletter','marketing','promotional','subscribe')): continue
            await loc.check(); filled.append(('checkbox','required_consent'))
        except Exception: pass
    return message_ok,unresolved,filled

async def find_submit(scope):
    loc=scope.locator('button[type="submit"]:visible,input[type="submit"]:visible')
    if await loc.count(): return loc.first
    btns=scope.locator('button:visible'); n=await btns.count(); best=None; bestscore=0
    targets=('send','submit','contact','enquire','inquire','send message','send enquiry','send inquiry','request','get in touch','contact us','start project')
    for i in range(n):
        b=btns.nth(i)
        try:
            txt=(await b.inner_text()).strip().lower(); sc=max([fuzz.ratio(txt,x) for x in targets]+[0])
            if sc>bestscore: best=b; bestscore=sc
        except Exception: pass
    return best if bestscore>=55 else None

async def attempt_route(browser,http_client,ai_client,cid,domain,fid,url):
    ev=EVIDENCE/f'{cid:09d}_{domain.replace(".","_")}'; ev.mkdir(parents=True,exist_ok=True)
    before=ev/f'v4-{fid}-01-before.png'; filledp=ev/f'v4-{fid}-02-filled.png'; after=ev/f'v4-{fid}-03-after.png'
    static=await static_probe(http_client,url)
    result={'form_id':fid,'url':url,'clicked':False,'status':'PRECHECK_FAILED','reason':'unknown','static':static,'before':str(before),'filled':str(filledp),'after':str(after)}
    ctx=await browser.new_context(viewport={'width':1440,'height':1100}); page=await ctx.new_page(); network=[]
    def on_response(resp):
        try:
            req=resp.request
            if req.method in ('POST','PUT','PATCH'):
                network.append({'url':resp.url,'status':resp.status,'method':req.method,'resource_type':req.resource_type})
        except Exception: pass
    page.on('response',on_response)
    try:
        await page.goto(url,wait_until='domcontentloaded',timeout=30000); await page.wait_for_timeout(1500); await page.screenshot(path=str(before),full_page=True)
        html=(await page.content()).lower(); body=(await page.locator('body').inner_text()).lower()
        if any(x in body for x in NO_SOLICIT): result.update(status='NO_SOLICITATION',reason='live_no_solicitation'); return result
        if any(x in body for x in TOPIC_ONLY): result.update(status='TOPIC_ONLY',reason='live_topic_only'); return result
        if any(x in html for x in CAPTCHA_HINTS): result.update(status='CAPTCHA_BLOCKED',reason='live_captcha'); return result
        best=await best_form(page)
        if not best: result.update(status='NO_USABLE_FORM',reason='no_form_scope'); return result
        score,frame,scope,metas,kinds,scope_name=best; result.update(form_score=score,scope=scope_name,kinds=kinds)
        if score<20 or 'message' not in kinds: result.update(status='NO_MESSAGE_FIELD',reason=f'best_score={score}'); return result
        msg_ok,unresolved,filled=await fill_scope(scope,metas,kinds,ai_client); result['filled_fields']=[x[0] for x in filled]
        result['unresolved_required']=[{k:v for k,v in m.items() if k in ('name','id','placeholder','label','type','tag')} for m in unresolved[:8]]
        if not msg_ok: result.update(status='NO_MESSAGE_FIELD',reason='message_fill_failed'); return result
        if unresolved: result.update(status='REQUIRED_UNKNOWN',reason='unmapped_required_fields'); return result
        submit=await find_submit(scope)
        if submit is None: result.update(status='NO_SUBMIT_BUTTON',reason='no_submit'); return result
        await page.screenshot(path=str(filledp),full_page=True)
        old_url=page.url; before_text=(await page.locator('body').inner_text()).lower(); before_forms=await page.locator('form:visible').count()
        await submit.click(timeout=10000); result['clicked']=True; await page.wait_for_timeout(5500)
        new_url=page.url; text=(await page.locator('body').inner_text()).lower(); html2=(await page.content()).lower(); after_forms=await page.locator('form:visible').count()
        post2xx=[x for x in network if 200<=x['status']<400]
        explicit=any(x in text for x in SUCCESS_WORDS) or any(x in html2 for x in SUCCESS_WORDS)
        redirect=(new_url!=old_url and bool(re.search(r'thank|success|submitted|confirmation|received',new_url,re.I)))
        validation=any(x in text for x in VALIDATION_WORDS) and not any(x in before_text for x in VALIDATION_WORDS)
        form_changed=after_forms<before_forms
        result['network']=network[-20:]; result['signals']={'explicit':explicit,'redirect':redirect,'post2xx':len(post2xx),'validation':validation,'form_changed':form_changed}
        if explicit: result.update(status='SUCCESS_CONFIRMED',reason='explicit_confirmation')
        elif redirect: result.update(status='SUCCESS_CONFIRMED',reason='confirmation_redirect')
        elif post2xx and form_changed and not validation: result.update(status='SUCCESS_CONFIRMED',reason='network_2xx_plus_form_transition')
        elif post2xx and not validation: result.update(status='SUBMIT_ACCEPTED',reason='network_2xx_no_explicit_confirmation')
        else: result.update(status='FAILED_CONFIRMATION',reason='clicked_without_sufficient_evidence')
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

async def save_precheck(pool,row,a):
    async with pool.acquire() as c:
        await c.execute('INSERT INTO sender_prechecks_v4(company_id,form_id,form_url,status,reason,details) VALUES($1,$2,$3,$4,$5,$6::jsonb)',row['company_id'],a.get('form_id'),a.get('url'),a.get('status'),a.get('reason'),json.dumps(a))

async def save_submission(pool,row,final,chosen,attempts):
    async with pool.acquire() as c:
        await c.execute('''INSERT INTO submissions_v3(company_id,form_id,form_url,status,confirmation,before_png,filled_png,after_png,result_json)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
        ON CONFLICT(company_id) DO UPDATE SET form_id=EXCLUDED.form_id,form_url=EXCLUDED.form_url,status=EXCLUDED.status,confirmation=EXCLUDED.confirmation,before_png=EXCLUDED.before_png,filled_png=EXCLUDED.filled_png,after_png=EXCLUDED.after_png,result_json=EXCLUDED.result_json''',row['company_id'],chosen.get('form_id'),chosen.get('url'),final,chosen.get('reason',''),chosen.get('before'),chosen.get('filled'),chosen.get('after'),json.dumps({'domain':row['domain'],'attempts':attempts,'batch_size':BATCH_SIZE,'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}))
        await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",final,row['company_id'])
        fp=((chosen.get('static') or {}).get('fingerprint'))
        if fp:
            vendor=(chosen.get('static') or {}).get('vendor','generic')
            recipe={'vendor':vendor,'scope':chosen.get('scope'),'kinds':chosen.get('kinds'),'signals':chosen.get('signals',{})}
            ok=1 if final in ('SUCCESS_CONFIRMED','SUBMIT_ACCEPTED') else 0
            await c.execute('''INSERT INTO form_recipes_v4(fingerprint,vendor,recipe_json,successes,failures) VALUES($1,$2,$3::jsonb,$4,$5)
            ON CONFLICT(fingerprint) DO UPDATE SET vendor=EXCLUDED.vendor,recipe_json=EXCLUDED.recipe_json,successes=form_recipes_v4.successes+$4,failures=form_recipes_v4.failures+$5,updated_at=now()''',fp,vendor,json.dumps(recipe),ok,1-ok)

async def defer_company(pool,row,status):
    async with pool.acquire() as c:
        await c.execute("UPDATE outreach_queue SET status=$1,updated_at=now() WHERE company_id=$2",status,row['company_id'])

async def worker(pool,browser,http_client,ai_client,gate,n):
    while True:
        if gate.claimed>=gate.n:return
        row=await claim_company(pool,gate)
        if not row:
            if gate.claimed>=gate.n:return
            await asyncio.sleep(.5); continue
        attempts=[]; clicked=None
        rs=await get_routes(pool,row['company_id'],row['preferred_form_id'])
        for r in rs:
            a=await attempt_route(browser,http_client,ai_client,row['company_id'],row['domain'],r['id'],r['page_url']); attempts.append(a)
            if not a.get('clicked'):
                await save_precheck(pool,row,a)
                continue
            clicked=a; break
        if clicked:
            await save_submission(pool,row,clicked['status'],clicked,attempts)
        else:
            # No commercial attempt was sent. Keep it separate from true submissions so it can be improved later without risking duplicate outreach.
            await defer_company(pool,row,'DEFERRED_PRECHECK')

async def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    pool=await asyncpg.create_pool(PG_DSN,min_size=4,max_size=max(24,SEND_WORKERS+10)); await init(pool); gate=Gate(BATCH_SIZE)
    limits=httpx.Limits(max_connections=max(32,SEND_WORKERS*4),max_keepalive_connections=max(16,SEND_WORKERS*2))
    async with httpx.AsyncClient(limits=limits) as http_client:
        async with httpx.AsyncClient() as ai_client:
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
                await asyncio.gather(*[asyncio.create_task(worker(pool,browser,http_client,ai_client,gate,i)) for i in range(SEND_WORKERS)])
                await browser.close()
    async with pool.acquire() as c:
        rows=await c.fetch("SELECT status,count(*) n FROM submissions_v3 GROUP BY status ORDER BY n DESC")
        ready=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY'")
        deferred=await c.fetchval("SELECT count(*) FROM outreach_queue WHERE status='DEFERRED_PRECHECK'")
    print('V4_BATCH_DONE claimed=',gate.claimed,' ready=',ready,' deferred=',deferred,' submissions=',[(r['status'],r['n']) for r in rows],flush=True)
    await pool.close()

if __name__=='__main__': asyncio.run(main())
