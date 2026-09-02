import json, html, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT/'app/marketing-agencies/sector-spec.json').read_text())
OUT = ROOT/'_site'
PAGE = OUT/'marketing-agencies'
PAGE.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT/'app/marketing-agencies/agency.css', PAGE/'agency.css')

G = {
  'brandName':'EXIOR',
  'paymentUrl':'https://buy.stripe.com/4gMbJ08rSdjl3Nx20R7IY00',
  'contactEmail':'contact@exior.io',
  'copyright':'© 2026 EXIOR. All rights reserved.'
}

def e(x): return html.escape(str(x))
def buy(label, cls='ag-buy'): return f'<a class="{cls}" href="{G["paymentUrl"]}">{e(label)}<span aria-hidden="true">↗</span></a>'
def heading(eyebrow, headline=None): return f'<header class="ag-heading"><p>{e(eyebrow)}</p>{f"<h2>{e(headline)}</h2>" if headline else ""}</header>'
def nums(items, fn): return ''.join(fn(x,i) for i,x in enumerate(items))

s=SPEC
parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EXIOR for Marketing Agencies</title><meta name="description" content="EXIOR installs an AI operating system for marketing agencies."><link rel="stylesheet" href="agency.css"></head><body><main class="ag-page" id="top">']
parts.append(f'<nav class="ag-nav ag-shell" aria-label="EXIOR"><a class="ag-brand" href="#top">EXIOR</a>{buy(s["hero"]["cta"],"ag-nav-buy")}</nav>')
h=s['hero']
parts.append(f'''<section class="ag-hero ag-shell"><div class="ag-hero-copy"><p class="ag-eyebrow">{e(h['eyebrow'])}</p><h1>{e(h['headline'])}</h1><p class="ag-hero-body">{e(h['subheadline'])}</p><div class="ag-hero-actions">{buy(h['cta'])}<b>{e(s['offer']['price'])}</b></div><small>{e(h['microcopy'])}</small></div><div class="ag-hero-visual" aria-hidden="true"><div class="ag-visual-top">{''.join(f'<span>{e(x)}</span>' for x in s['engine']['inside'][:3])}</div><div class="ag-visual-lines"><i></i><i></i><i></i><i></i></div><div class="ag-visual-core"><b>EXIOR</b><span>{e(s['offer']['product'])}</span></div><div class="ag-visual-lines ag-bottom"><i></i><i></i><i></i><i></i></div><div class="ag-visual-bottom">{''.join(f'<span>{e(x)}</span>' for x in [s['engine']['loop'][3],s['engine']['loop'][4],s['engine']['loop'][6]])}</div><div class="ag-corner ag-tl"></div><div class="ag-corner ag-tr"></div><div class="ag-corner ag-bl"></div><div class="ag-corner ag-br"></div></div></section>''')
m=s['marketSignals']; parts.append(f'<section class="ag-signals ag-shell">{heading(m["eyebrow"])}<div class="ag-signal-grid">'+''.join(f'<article><b>{e(x["stat"])}</b><p>{e(x["label"])}</p></article>' for x in m['items'])+'</div></section>')
o=s['opportunity']; parts.append(f'<section class="ag-section ag-light ag-opportunity"><div class="ag-shell">{heading(o["eyebrow"],o["headline"])}<p class="ag-lead">{e(o["body"])}</p><div class="ag-opportunity-grid">'+nums(o['cards'],lambda x,i:f'<article><span>{i+1:02d}</span><h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></article>')+'</div></div></section>')
i=s['installed']; parts.append(f'<section class="ag-section ag-shell ag-installed">{heading(i["eyebrow"],i["headline"])}<div class="ag-module-grid">'+nums(i['modules'],lambda x,n:f'<article><header><span>{n+1:02d}</span><i></i></header><h3>{e(x["title"])}</h3><p>{e(x["description"])}</p></article>')+f'</div><div class="ag-cta-band"><b>{e(s["offer"]["price"])}</b>{buy(h["cta"])}</div></section>')
a=s['augmentedAgency']; parts.append(f'<section class="ag-section ag-augmented"><div class="ag-shell">{heading(a["eyebrow"],a["headline"])}<div class="ag-capabilities">'+nums(a['capabilities'],lambda x,n:f'<article><span>{n+1:02d}</span><h3>{e(x)}</h3><i aria-hidden="true">↗</i></article>')+'</div></div></section>')
eng=s['engine']; parts.append(f'<section class="ag-section ag-shell ag-engine">{heading(eng["eyebrow"],eng["headline"])}<p class="ag-lead ag-dark-lead">{e(eng["body"])}</p><div class="ag-engine-map"><div class="ag-engine-side"><h3>{e(eng["insideLabel"])}</h3><div>'+''.join(f'<span>{e(x)}</span>' for x in eng['inside'])+f'</div></div><div class="ag-engine-core"><i></i><b>EXIOR</b><span>{e(eng["loop"][3])}<br>{e(eng["loop"][4])}</span><i></i></div><div class="ag-engine-side ag-outside"><h3>{e(eng["outsideLabel"])}</h3><div>'+''.join(f'<span>{e(x)}</span>' for x in eng['outside'])+'</div></div></div><div class="ag-loop">'+''.join(f'<div><span>{e(x)}</span>{"<i>→</i>" if n<len(eng["loop"])-1 else ""}</div>' for n,x in enumerate(eng['loop']))+f'</div><blockquote>{e(eng["statement"])}</blockquote></section>')
d=s['decisionEngine']; parts.append(f'<section class="ag-section ag-decision"><div class="ag-shell">{heading(d["eyebrow"],d["headline"])}<div class="ag-ranking">'+nums(d['priorities'],lambda x,n:f'<article><b>{n+1:02d}</b><h3>{e(x)}</h3></article>')+f'</div><p class="ag-disclaimer">{e(d["disclaimer"])}</p><div class="ag-cta-band ag-inverse"><b>{e(s["offer"]["price"])}</b>{buy(s["offer"]["cta"])}</div></div></section>')
of=s['offer']; parts.append(f'<section class="ag-section ag-shell" id="offer"><div class="ag-offer"><div class="ag-offer-copy"><span>{e(of["product"])}</span><h2>{e(of["headline"])}</h2><p>{e(of["description"])}</p></div><div class="ag-offer-panel"><b class="ag-price">{e(of["price"])}</b><h3>{e(of["deliverablesLabel"])}</h3><ul>'+nums(of['deliverables'],lambda x,n:f'<li><span>{n+1:02d}</span>{e(x)}</li>')+f'</ul><div class="ag-delivery"><span>{e(of["deliveryLabel"])}</span><p>{e(of["delivery"])}</p></div>{buy(of["cta"])}</div></div></section>')
how=s['howItWorks']; parts.append(f'<section class="ag-section ag-how ag-light"><div class="ag-shell">{heading(how["eyebrow"])}<div class="ag-steps">'+nums(how['steps'],lambda x,n:f'<article><b>{n+1:02d}</b><h3>{e(x["title"])}</h3><p>{e(x["description"])}</p>{"<i>→</i>" if n<len(how["steps"])-1 else ""}</article>')+'</div></div></section>')
c=s['continuous']; parts.append(f'<section class="ag-section ag-shell ag-continuous">{heading(c["eyebrow"],c["headline"])}<div class="ag-continuous-list">'+nums(c['items'],lambda x,n:f'<article><span>{n+1:02d}</span><h3>{e(x["title"])}</h3><p>{e(x["description"])}</p></article>')+'</div></section>')
f=s['faq']; parts.append(f'<section class="ag-section ag-faq"><div class="ag-shell">{heading(f["eyebrow"])}<div class="ag-questions">'+nums(f['questions'],lambda x,n:f'<article><span>{n+1:02d}</span><h3>{e(x)}</h3></article>')+'</div></div></section>')
fc=s['finalCta']; parts.append(f'<section class="ag-final ag-light"><div class="ag-shell"><h2>{e(fc["headline"])}</h2><p>{e(fc["body"])}</p><b>{e(fc["price"])}</b>{buy(fc["cta"])}</div></section>')
parts.append(f'<footer class="ag-footer ag-shell"><div><b>EXIOR</b><p>{e(s["footer"]["description"])}</p></div><nav><a href="mailto:{G["contactEmail"]}">{G["contactEmail"]}</a></nav><small>{e(G["copyright"])}</small></footer>{buy(h["cta"],"ag-mobile-buy")}</main></body></html>')
(PAGE/'index.html').write_text(''.join(parts), encoding='utf-8')
(OUT/'404.html').write_text('<!doctype html><meta charset="utf-8"><title>EXIOR</title><body style="margin:0;background:#050607;color:#fff;font-family:Arial,sans-serif;display:grid;place-items:center;min-height:100vh"><div><b style="letter-spacing:.25em">EXIOR</b></div></body>',encoding='utf-8')
(OUT/'CNAME').write_text('exior.io\n',encoding='utf-8')
print('built', PAGE/'index.html')
