import asyncio, importlib.util, re
from rapidfuzz import fuzz

BASE='/opt/exior-contact-indexer/sender-v4.py'
spec=importlib.util.spec_from_file_location('sender_v4_base',BASE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def semantic(meta):
    t=m.normtxt(meta); typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower(); role=(meta.get('role') or '').lower(); ac=(meta.get('autocomplete') or '').lower()
    if typ=='email' or ac=='email' or re.search(r'\b(e-?mail|work email|business email)\b',t): return 'email'
    if typ=='tel' or ac=='tel' or re.search(r'\b(phone|telephone|mobile|tel|contact number)\b',t): return 'phone'
    if ac=='given-name' or re.search(r'\b(first name|given name|forename)\b',t): return 'first_name'
    if ac=='family-name' or re.search(r'\b(last name|surname|family name)\b',t): return 'last_name'
    if ac=='name' or re.search(r'\b(full name|your name|contact name|name)\b',t): return 'name'
    if re.search(r'\b(company|organisation|organization|business|agency|company name|organisation name|business name)\b',t): return 'company'
    if re.search(r'\b(website|web site|company url|site url|domain|url)\b',t): return 'website'
    if re.search(r'\b(subject|topic|reason for contacting|reason for enquiry|reason for inquiry|nature of enquiry|department)\b',t): return 'subject'
    if tag=='textarea': return 'message'
    needles=('message','how can we help','tell us about','tell us more','project','brief','inquiry','enquiry','details','comments','what can we help','your needs','describe','what do you need','project details','how may we help','how can i help','anything else','additional information','what are you looking for','your request','your enquiry','your inquiry','project description','tell us what','how can our team help','what would you like','tell us how','your project','what brings you here')
    if any(x in t for x in needles): return 'message'
    if role=='textbox' and meta.get('contenteditable'): return 'message'
    return 'unknown'
m.semantic=semantic

async def score_scope(scope):
    try: metas=await m.visible_meta(scope)
    except Exception: return -999,[],[]
    kinds=[semantic(x) for x in metas]
    score=0
    # Any visible textarea/message field is enough to clear the base V4 score gate.
    if 'message' in kinds or any(x.get('tag')=='textarea' for x in metas): score+=25
    if 'email' in kinds: score+=7
    if any(x in kinds for x in ('name','first_name','last_name')): score+=4
    if 'company' in kinds: score+=3
    if 'phone' in kinds: score+=2
    try:
        if await scope.locator('button[type="submit"]:visible,input[type="submit"]:visible').count(): score+=5
        elif await scope.locator('button:visible').count(): score+=2
    except Exception: pass
    return score,metas,kinds
m.score_scope=score_scope

async def best_form(page):
    cand=[]
    for frame in page.frames:
        try:
            forms=frame.locator('form:visible'); n=min(await forms.count(),20)
            for i in range(n):
                s=forms.nth(i); sc,metas,kinds=await score_scope(s); cand.append((sc,frame,s,metas,kinds,f'form[{i}]'))
            sc,metas,kinds=await score_scope(frame)
            if sc>=20: cand.append((sc-1,frame,frame,metas,kinds,'frame-root'))
        except Exception: continue
    if not cand: return None
    cand.sort(key=lambda x:x[0],reverse=True); return cand[0]
m.best_form=best_form

async def choose_select(loc):
    try:
        opts=await loc.locator('option').all_text_contents(); vals=await loc.locator('option').evaluate_all('els=>els.map(e=>e.value)')
        candidates=[]
        good=m.GENERIC_SELECT_GOOD+('contact','new project','project enquiry','project inquiry','services','other enquiry','general enquiry','general inquiry','other','not sure')
        bad=m.GENERIC_SELECT_BAD+('employment','vacancy','technical support','customer support','careers')
        for txt,val in zip(opts,vals):
            s=(txt or '').strip().lower()
            if not val or not s or s in ('select','choose','please select','please choose','-'): continue
            sc=max([fuzz.partial_ratio(s,x) for x in good]+[0])-max([fuzz.partial_ratio(s,x) for x in bad]+[0])
            candidates.append((sc,val,txt))
        candidates.sort(reverse=True,key=lambda x:x[0])
        if candidates and candidates[0][0]>=0:
            _,val,txt=candidates[0]; await loc.select_option(value=val); return True,txt
    except Exception: pass
    return False,None
m.choose_select=choose_select

async def fill_scope(scope,metas,kinds,ai_client):
    controls=scope.locator('input:visible, textarea:visible, select:visible, [contenteditable="true"]:visible, [role="textbox"]:visible')
    message_ok=False; unresolved=[]; filled=[]
    if 'message' not in kinds:
        for i,x in enumerate(metas):
            if x.get('tag')=='textarea' or (x.get('role')=='textbox' and x.get('contenteditable')):
                kinds[i]='message'; break
    for meta,k in zip(metas,kinds):
        loc=controls.nth(meta['i']); typ=(meta.get('type') or '').lower(); tag=(meta.get('tag') or '').lower(); t=m.normtxt(meta)
        if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue
        if k=='unknown' and meta.get('required') and m.ENABLE_LOCAL_AI:
            k=await m.ai_classify_unknown(ai_client,meta)
        try:
            if tag=='select':
                if meta.get('required'):
                    ok,v=await choose_select(loc)
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
            elif meta.get('required'):
                # Truthful, non-invented generic answers for common routing fields.
                if any(x in t for x in ('job title','your role','position','title')): val='Founder'
                elif any(x in t for x in ('city','town')): val='Paris'
                elif 'country' in t: val='France'
                elif any(x in t for x in ('how did you hear','how did you find','where did you hear')): val='Website'
                elif any(x in t for x in ('budget','investment')): val='Not specified'
                elif any(x in t for x in ('timeline','when do you need','timeframe')): val='Flexible'
                elif any(x in t for x in ('company size','team size','employees')): val='Not specified'
                elif typ in ('text','search') and any(x in t for x in ('company','business','organisation','organization')): val=m.COMPANY
            if val is not None:
                await loc.fill(val); filled.append((k if k!='unknown' else 'generic',str(val)[:80]))
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
m.fill_scope=fill_scope

if __name__=='__main__': asyncio.run(m.main())
