#!/usr/bin/env python3
import csv,json,os,time
from pathlib import Path
from urllib.parse import urlparse
from ddgs import DDGS

APP=Path('/opt/exior-contact-indexer'); DATA=APP/'data'; DATA.mkdir(parents=True,exist_ok=True)
LIMIT=max(50,min(int(os.getenv('PROSPECT_LIMIT','500')),500))
OUT=DATA/'ai-agent-top-500.csv'; OUTJ=DATA/'ai-agent-top-500.json'
SEGMENTS={
 'marketing_agency':['marketing agency','performance marketing agency','SEO agency','creative agency'],
 'recruiting':['recruitment agency','staffing agency','executive search firm'],
 'accounting':['accounting firm','bookkeeping firm','CPA firm'],
 'property_management':['property management company','real estate property management'],
 'b2b_services':['B2B service company','consulting firm','managed service provider']}
SIGNALS=['hiring','careers','growing team','HubSpot','Salesforce','Zapier','automation','AI','operations']
BUYER_WORDS=('founder','ceo','owner','coo','operations','managing director','head of operations')
STACK_WORDS=('hubspot','salesforce','zapier','make.com','n8n','crm','automation',' ai ')
GROWTH_WORDS=('hiring','careers','growing','new office','expanding','team of','our team')
PAIN_WORDS=('manual','repetitive','workflow','operations','reporting','follow-up','follow up','admin','process')
EXCLUDE=('facebook.com','linkedin.com','instagram.com','youtube.com','clutch.co','yelp.com','upwork.com','fiverr.com')

def domain(u):
 try:
  h=urlparse(u).netloc.lower().split(':')[0]
  return h[4:] if h.startswith('www.') else h
 except:return ''

def score(text,segment):
 t=' '+(text or '').lower()+' '; s=35
 s+=20 if any(x in t for x in BUYER_WORDS) else 0
 s+=15 if any(x in t for x in STACK_WORDS) else 0
 s+=15 if any(x in t for x in GROWTH_WORDS) else 0
 s+=10 if any(x in t for x in PAIN_WORDS) else 0
 s+=5 if segment in ('marketing_agency','recruiting','accounting') else 0
 return min(s,100)

rows={}
ddgs=DDGS()
for seg,terms in SEGMENTS.items():
 for term in terms:
  for sig in SIGNALS:
   q=f'"{term}" "{sig}" company'
   try: results=list(ddgs.text(q,max_results=20))
   except Exception: continue
   for r in results:
    u=r.get('href') or r.get('url') or ''; d=domain(u)
    if not d or any(x in d for x in EXCLUDE): continue
    text=' '.join([r.get('title') or '',r.get('body') or '',q])
    sc=score(text,seg)
    cur=rows.get(d)
    item={'domain':d,'website':'https://'+d,'segment':seg,'score':sc,'evidence':text[:900],'source_query':q}
    if not cur or sc>cur['score']: rows[d]=item
   time.sleep(.08)
ranked=sorted(rows.values(),key=lambda x:(x['score'],x['segment']),reverse=True)[:LIMIT]
for i,x in enumerate(ranked,1): x['rank']=i
with OUT.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['rank','score','segment','domain','website','source_query','evidence']); w.writeheader(); w.writerows(ranked)
OUTJ.write_text(json.dumps({'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'offer':'https://exior.io/ai-agent','count':len(ranked),'prospects':ranked},indent=2),encoding='utf-8')
print(json.dumps({'status':'DONE','count':len(ranked),'csv':str(OUT),'json':str(OUTJ),'top_score':ranked[0]['score'] if ranked else None}))
