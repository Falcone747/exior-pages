import json, html, pathlib, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'app/marketing-agencies/sector-spec.json').read_text())
OUT=ROOT/'_site'; PAGE=OUT/'marketing-agencies'; PAGE.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'app/marketing-agencies/agency.css',PAGE/'agency.css')
shutil.copy2(ROOT/'app/marketing-agencies/premium.css',PAGE/'premium.css')
PAY='https://buy.stripe.com/4gMbJ08rSdjl3Nx20R7IY00'
def e(x): return html.escape(str(x))
def cta(label,cls='btn primary'): return f'<a class="{cls}" href="{PAY}"><span>{e(label)}</span><span aria-hidden="true">↗</span></a>'
def tag(txt): return f'<div class="eyebrow">{e(txt)}</div>'
parts=[]
parts.append('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#070b14"><title>EXIOR for Marketing Agencies</title><meta name="description" content="EXIOR installs a private intelligence and execution layer for marketing agencies."><link rel="stylesheet" href="agency.css"><link rel="stylesheet" href="premium.css"></head><body>')
parts.append('<div class="site-shell">')
parts.append(f'<header class="nav"><a class="brand" href="#top">EXIOR</a><div class="nav-meta">FOR MARKETING AGENCIES</div>{cta("Install EXIOR — US$500","btn nav-cta")}</header>')
h=s['hero']
parts.append(f'''<main id="top"><section class="hero"><div class="hero-copy">{tag(h['eyebrow'])}<h1>{e(h['headline'])}</h1><p class="hero-lead">{e(h['subheadline'])}</p><div class="hero-actions">{cta(h['cta'])}<span class="micro">{e(h['microcopy'])}</span></div></div><div class="hero-system" aria-label="EXIOR operating system visualization"><div class="system-glow"></div><div class="system-top"><span>Agency intelligence</span><span>01 / Operating layer</span></div><div class="system-center"><div class="core"><small>PRIVATE SYSTEM</small><strong>EXIOR</strong><span>Agency OS</span></div><div class="orbit orbit-a"><i></i><i></i><i></i></div><div class="orbit orbit-b"><i></i><i></i><i></i></div></div><div class="system-grid"><span>REVENUE</span><span>MARGIN</span><span>CAPACITY</span><span>MARKET</span><span>AI</span><span>EXECUTION</span></div></div></section>''')
o=s['outcomes']; parts.append(f'<section class="section light"><div class="section-head">{tag(o["eyebrow"])}<h2>{e(o["headline"])}</h2></div><div class="outcome-grid">')
for idx,x in enumerate(o['items'],1): parts.append(f'<article class="outcome"><span class="num">0{idx}</span><h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></article>')
parts.append('</div></section>')
sys=s['system']; parts.append(f'<section class="section dark-system"><div class="section-head split">{tag(sys["eyebrow"])}<div><h2>{e(sys["headline"])}</h2><p>{e(sys["body"])}</p></div></div><div class="bento">')
for idx,x in enumerate(sys['modules'],1):
    cls='module featured' if idx==1 else 'module'
    parts.append(f'<article class="{cls}"><span class="num">0{idx}</span><div class="module-line"></div><h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></article>')
parts.append('</div></section>')
eng=s['engine']; parts.append(f'<section class="section engine"><div class="section-head">{tag(eng["eyebrow"])}<h2>{e(eng["headline"])}</h2><p class="section-lead">{e(eng["body"])}</p></div><div class="engine-frame"><div class="engine-col"><small>INSIDE THE AGENCY</small>')
for x in eng['inside']: parts.append(f'<span>{e(x)}</span>')
parts.append('''</div><div class="engine-core"><div class="core-kicker">LIVE DECISION LAYER</div><div class="engine-priority"><header><strong>EXIOR</strong><span>PRIORITY QUEUE</span></header><div class="priority-row"><b>01</b><span>Protect margin on at-risk accounts</span><em>HIGH</em></div><div class="priority-row"><b>02</b><span>Expand highest-value client accounts</span><em>HIGH</em></div><div class="priority-row"><b>03</b><span>Automate recurring delivery work</span><em>MED</em></div></div><div class="engine-signal"><div><small>REVENUE SIGNALS</small><strong>12</strong></div><div><small>AUTOMATION CANDIDATES</small><strong>8</strong></div></div><div class="engine-status"><i></i><span>CONTINUOUSLY ANALYZING</span></div></div><div class="engine-col right"><small>OUTSIDE THE AGENCY</small>''')
for x in eng['outside']: parts.append(f'<span>{e(x)}</span>')
parts.append('</div></div><div class="loop">')
for idx,x in enumerate(eng['loop']): parts.append(f'<span>{e(x)}{(" →" if idx < len(eng["loop"])-1 else "")}</span>')
parts.append('</div></section>')
of=s['offer']; parts.append(f'<section class="section offer"><div class="offer-copy">{tag(of["eyebrow"])}<div class="price">{e(of["price"])}</div><h2>{e(of["headline"])}</h2><p>{e(of["description"])}</p>{cta(of["cta"],"btn primary large")}</div><div class="offer-card"><div class="offer-card-head"><span>{e(of["product"])}</span><span>INITIAL INSTALLATION</span></div><div class="deliverables">')
for idx,x in enumerate(of['deliverables'],1): parts.append(f'<div><span>0{idx}</span><p>{e(x)}</p></div>')
parts.append(f'</div><div class="delivery"><span>DELIVERY</span><p>{e(of["delivery"])}</p></div></div></section>')
pr=s['process']; parts.append(f'<section class="section light process"><div class="section-head">{tag(pr["eyebrow"])}<h2>{e(pr["headline"])}</h2></div><div class="process-grid">')
for idx,x in enumerate(pr['steps'],1): parts.append(f'<article><span class="num">0{idx}</span><h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></article>')
parts.append('</div></section>')
parts.append('<section class="section faq"><div class="faq-title"><div class="eyebrow">FAQ</div><h2>Everything required to start.</h2></div><div class="faq-list">')
for idx,x in enumerate(s['faq'],1): parts.append(f'<details><summary><span>0{idx}</span>{e(x["q"])}<b>+</b></summary><p>{e(x["a"])}</p></details>')
parts.append('</div></section>')
f=s['final']; parts.append(f'<section class="final"><div class="final-grid"></div><div class="final-copy"><span class="eyebrow">EXIOR AGENCY OS</span><h2>{e(f["headline"])}</h2><p>{e(f["body"])}</p>{cta(f["cta"],"btn final-cta")}</div><div class="final-price">US$500</div></section>')
parts.append(f'</main><footer><div><strong>EXIOR</strong><p>{e(s["footer"])}</p></div><a href="mailto:contact@exior.io">contact@exior.io</a><span>© 2026 EXIOR</span></footer></div></body></html>')
(PAGE/'index.html').write_text(''.join(parts),encoding='utf-8')
(OUT/'404.html').write_text('<!doctype html><meta charset="utf-8"><title>EXIOR</title><body style="margin:0;background:#070b14;color:#fff;font:16px Arial;display:grid;place-items:center;min-height:100vh"><b style="letter-spacing:.25em">EXIOR</b></body>',encoding='utf-8')
(OUT/'CNAME').write_text('exior.io\n',encoding='utf-8')
print('built',PAGE/'index.html')