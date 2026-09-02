import asyncio, importlib.util, json, os, re
import httpx

BASE='/opt/exior-contact-indexer/sender-v4.py'
spec=importlib.util.spec_from_file_location('sender_v4_base',BASE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434')
OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','qwen3:1.7b')
AI_TIMEOUT=float(os.getenv('AI_TIMEOUT','20'))

ALLOWED_ROLES={'email','phone','first_name','last_name','name','company','website','subject','message','job_title','city','country','unknown'}

async def llm_plan(metas):
    payload=[]
    for i,x in enumerate(metas):
        payload.append({
            'i':i,'tag':x.get('tag'),'type':x.get('type'),'name':x.get('name'),'id':x.get('id'),
            'placeholder':x.get('placeholder'),'aria':x.get('aria'),'label':x.get('label'),
            'autocomplete':x.get('autocomplete'),'required':bool(x.get('required')),'nearby':(x.get('nearby') or '')[:400]
        })
    prompt='''You classify fields of a B2B company contact form. Return JSON only, exactly {"roles":[{"i":0,"role":"email"},...]}. Allowed roles: email, phone, first_name, last_name, name, company, website, subject, message, job_title, city, country, unknown. Identify the long free-text project/enquiry field as message. Do not invent fields. Every input index must appear exactly once.\nFIELDS='''+json.dumps(payload,ensure_ascii=False)
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as c:
            r=await c.post(OLLAMA_URL.rstrip('/')+'/api/chat',json={
                'model':OLLAMA_MODEL,'stream':False,'format':'json',
                'options':{'temperature':0},
                'messages':[{'role':'user','content':prompt}]
            })
            r.raise_for_status()
            txt=r.json().get('message',{}).get('content','{}')
            data=json.loads(txt)
            roles=['unknown']*len(metas)
            for item in data.get('roles',[]):
                try:
                    idx=int(item.get('i')); role=str(item.get('role','unknown')).strip().lower()
                    if 0<=idx<len(roles) and role in ALLOWED_ROLES: roles[idx]=role
                except Exception: pass
            return roles
    except Exception:
        return None

def heuristic_roles(metas):
    return [m.semantic(x) for x in metas]

async def score_scope_ai(scope):
    try: metas=await m.visible_meta(scope)
    except Exception: return -999,[],[]
    roles=heuristic_roles(metas)
    has_message='message' in roles or any(x.get('tag')=='textarea' for x in metas)
    if not has_message and len(metas)>=2:
        plan=await llm_plan(metas)
        if plan: roles=plan
    if 'message' not in roles:
        for i,x in enumerate(metas):
            if x.get('tag')=='textarea': roles[i]='message'; break
    score=0
    if 'message' in roles: score+=25
    if 'email' in roles: score+=7
    if any(x in roles for x in ('name','first_name','last_name')): score+=4
    if 'company' in roles: score+=3
    if 'phone' in roles: score+=2
    try:
        if await scope.locator('button[type="submit"]:visible,input[type="submit"]:visible').count(): score+=5
        elif await scope.locator('button:visible').count(): score+=2
    except Exception: pass
    return score,metas,roles

async def best_form_ai(page):
    candidates=[]
    for frame in page.frames:
        try:
            forms=frame.locator('form:visible'); n=min(await forms.count(),20)
            for i in range(n):
                scope=forms.nth(i); sc,metas,roles=await score_scope_ai(scope)
                candidates.append((sc,frame,scope,metas,roles,f'form[{i}]'))
            # custom JS forms / iframe root
            sc,metas,roles=await score_scope_ai(frame)
            if sc>=20: candidates.append((sc-1,frame,frame,metas,roles,'frame-root'))
        except Exception: continue
    if not candidates: return None
    candidates.sort(key=lambda z:z[0],reverse=True)
    return candidates[0]

m.best_form=best_form_ai
m.score_scope=score_scope_ai

async def choose_select_any(loc):
    try:
        opts=await loc.locator('option').all_text_contents(); vals=await loc.locator('option').evaluate_all('els=>els.map(e=>e.value)')
        good=('general','business','sales','new business','project','other','enquiry','inquiry','partnership','marketing','contact','services')
        bad=('job','career','support','press','media','investor','billing','employment')
        ranked=[]
        for txt,val in zip(opts,vals):
            s=(txt or '').strip().lower()
            if not val or not s or 'select' in s or 'choose' in s: continue
            score=sum(5 for x in good if x in s)-sum(8 for x in bad if x in s)
            ranked.append((score,val,txt))
        if ranked:
            ranked.sort(reverse=True,key=lambda x:x[0])
            score,val,txt=ranked[0]
            if score>=0:
                await loc.select_option(value=val); return True,txt
    except Exception: pass
    return False,None
m.choose_select=choose_select_any

async def fill_scope_ai(scope,metas,kinds,ai_client):
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    # If heuristic/AI still missed message, longest textarea/textbox becomes message.
    if 'message' not in kinds:
        for i,x in enumerate(metas):
            if x.get('tag')=='textarea' or (x.get('role')=='textbox' and x.get('contenteditable')):
                kinds[i]='message'; break
    message_ok=False; unresolved=[]; filled=[]
    for meta,k in zip(metas,kinds):
        loc=controls.nth(meta['i']); typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower()
        if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
        try:
            if tag=='select':
                if meta.get('required'):
                    ok,v=await choose_select_any(loc)
                    if ok: filled.append(('select',v))
                    else: unresolved.append(meta)
                continue
            val=None
            if k=='email': val=m.EMAIL
            elif k=='phone': val=m.PHONE
            elif k=='first_name': val=m.FIRST_NAME
            elif k=='last_name': val=m.LAST_NAME
            elif k=='name': val=m.NAME
            elif k=='company': val=m.COMPANY
            elif k=='website': val=m.WEBSITE
            elif k=='subject': val=m.SUBJECT
            elif k=='message': val=m.MESSAGE; message_ok=True
            elif k=='job_title': val='Founder'
            elif k=='city': val='Paris'
            elif k=='country': val='France'
            if val is not None:
                await loc.fill(val); filled.append((k,str(val)[:80]))
            elif meta.get('required'): unresolved.append(meta)
        except Exception:
            if meta.get('required'): unresolved.append(meta)
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

m.fill_scope=fill_scope_ai

if __name__=='__main__':
    asyncio.run(m.main())
