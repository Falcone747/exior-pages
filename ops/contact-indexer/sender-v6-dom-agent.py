import asyncio, importlib.util, json, os, re
import httpx

BASE='/opt/exior-contact-indexer/sender-v4.py'
spec=importlib.util.spec_from_file_location('sender_v4_base', BASE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434')
OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','qwen3:1.7b')
AI_TIMEOUT=float(os.getenv('AI_TIMEOUT','35'))

ROLE_VALUES={
 'email':m.EMAIL,'phone':m.PHONE,'first_name':m.FIRST_NAME,'last_name':m.LAST_NAME,
 'name':m.NAME,'company':m.COMPANY,'website':m.WEBSITE,'subject':m.SUBJECT,
 'message':m.MESSAGE,'job_title':'Founder','city':'Paris','country':'France'
}
ALLOWED=set(ROLE_VALUES)|{'unknown'}

async def ollama_json(prompt):
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as c:
            r=await c.post(OLLAMA_URL.rstrip('/')+'/api/chat',json={
                'model':OLLAMA_MODEL,'stream':False,'format':'json',
                'options':{'temperature':0,'num_ctx':8192},
                'messages':[{'role':'user','content':prompt}]})
            r.raise_for_status()
            return json.loads(r.json().get('message',{}).get('content','{}'))
    except Exception:
        return None

async def extract_candidate(scope, frame_idx, form_idx, scope_name):
    try:
        metas=await m.visible_meta(scope)
    except Exception:
        return None
    if not metas: return None
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    fields=[]
    for meta in metas:
        item={k:meta.get(k) for k in ('i','tag','type','name','id','placeholder','aria','label','title','autocomplete','required','nearby')}
        if meta.get('tag')=='select':
            try:
                loc=controls.nth(meta['i'])
                item['options']=(await loc.locator('option').all_text_contents())[:30]
            except Exception: item['options']=[]
        fields.append(item)
    buttons=[]
    try:
        btns=scope.locator('button:visible,input[type="submit"]:visible')
        for i in range(min(await btns.count(),15)):
            b=btns.nth(i)
            try:
                txt=((await b.inner_text()) or (await b.get_attribute('value')) or '').strip()
            except Exception: txt=''
            buttons.append({'i':i,'text':txt[:160],'type':await b.get_attribute('type')})
    except Exception: pass
    try: text=(await scope.inner_text())[:2500]
    except Exception: text=''
    return {'frame_idx':frame_idx,'form_idx':form_idx,'scope_name':scope_name,'fields':fields,'buttons':buttons,'text':text}

async def plan_page(page):
    candidates=[]; scopes=[]
    for fi,frame in enumerate(page.frames):
        try:
            forms=frame.locator('form:visible'); n=min(await forms.count(),20)
            for j in range(n):
                scope=forms.nth(j)
                c=await extract_candidate(scope,fi,j,f'form[{j}]')
                if c: candidates.append(c); scopes.append(scope)
            # root fallback for JS/custom forms without <form>
            root=frame
            c=await extract_candidate(root,fi,-1,'frame-root')
            if c and any(x.get('tag')=='textarea' for x in c['fields']):
                candidates.append(c); scopes.append(root)
        except Exception: continue
    if not candidates: return None
    compact=[]
    for idx,c in enumerate(candidates):
        compact.append({'candidate':idx,'text':c['text'][:1200],'fields':c['fields'],'buttons':c['buttons']})
    prompt='''You are mapping a rendered B2B contact form. Choose the ONE candidate that is actually suitable for a normal business/project enquiry. Do not choose careers, support, press, login, newsletter or search forms. Return JSON only:
{"candidate":0,"fields":[{"i":0,"role":"email","value":null},{"i":1,"role":"message","value":null}],"selects":[{"i":4,"option":"General enquiry"}],"submit_text":"Send","confidence":0.0}
Allowed roles: email, phone, first_name, last_name, name, company, website, subject, message, job_title, city, country, unknown.
For value use null: the executor already knows verified sender values. For required select fields choose a neutral business/general/project/enquiry option from the supplied options. Identify the long free-text enquiry/project field as message. Never invent field indexes or options. CANDIDATES='''+json.dumps(compact,ensure_ascii=False)
    plan=await ollama_json(prompt)
    if not plan: return None
    try: ci=int(plan.get('candidate'))
    except Exception: return None
    if not (0<=ci<len(candidates)): return None
    return candidates[ci],scopes[ci],plan

async def best_form_ai(page):
    planned=await plan_page(page)
    if not planned: return None
    c,scope,plan=planned
    metas=await m.visible_meta(scope)
    roles=['unknown']*len(metas)
    for x in plan.get('fields',[]):
        try:
            i=int(x.get('i')); role=str(x.get('role','unknown')).lower()
            if 0<=i<len(roles) and role in ALLOWED: roles[i]=role
        except Exception: pass
    # deterministic fallback for obvious fields model missed
    for i,meta in enumerate(metas):
        if roles[i]=='unknown':
            r=m.semantic(meta)
            if r!='unknown': roles[i]=r
    if 'message' not in roles:
        for i,meta in enumerate(metas):
            if meta.get('tag')=='textarea': roles[i]='message'; break
    score=30 if 'message' in roles else 0
    score+=8 if 'email' in roles else 0
    score+=4 if any(x in roles for x in ('name','first_name','last_name')) else 0
    scope._exior_plan=plan
    return score,None,scope,metas,roles,c['scope_name']

m.best_form=best_form_ai
m.score_scope=lambda scope: (_ for _ in ()).throw(RuntimeError('unused'))

async def fill_scope_ai(scope,metas,kinds,ai_client):
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    plan=getattr(scope,'_exior_plan',{}) or {}
    select_choices={}
    for x in plan.get('selects',[]):
        try: select_choices[int(x.get('i'))]=str(x.get('option','')).strip()
        except Exception: pass
    message_ok=False; unresolved=[]; filled=[]
    for meta,role in zip(metas,kinds):
        loc=controls.nth(meta['i']); typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower()
        if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
        try:
            if tag=='select':
                if meta.get('required'):
                    choice=select_choices.get(meta['i'])
                    ok=False
                    if choice:
                        opts=await loc.locator('option').all_text_contents()
                        for txt in opts:
                            if txt.strip().lower()==choice.lower():
                                await loc.select_option(label=txt); ok=True; filled.append(('select',txt)); break
                    if not ok:
                        ok,v=await m.choose_select(loc)
                        if ok: filled.append(('select',v))
                        else: unresolved.append(meta)
                continue
            val=ROLE_VALUES.get(role)
            if val is not None:
                await loc.fill(val); filled.append((role,str(val)[:80])); message_ok=message_ok or role=='message'
            elif meta.get('required'):
                unresolved.append(meta)
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

if __name__=='__main__': asyncio.run(m.main())
