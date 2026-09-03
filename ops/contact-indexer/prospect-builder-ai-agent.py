#!/usr/bin/env python3
import csv,json,os,re,sqlite3,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.parse import urljoin,urlparse
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

APP=Path('/opt/exior-contact-indexer'); DATA=APP/'data'; DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'index.db'; LIMIT=max(50,min(int(os.getenv('PROSPECT_LIMIT','500')),500))
OUT=DATA/'ai-agent-top-500.csv'; OUTJ=DATA/'ai-agent-top-500.json'
UA={'User-Agent':'Mozilla/5.0 (compatible; EXIORBuyerQualification/1.0)'}

DIR_HOSTS=('clutch.co','goodfirms.co','designrush.com','themanifest.com','sortlist.com','agencyspotter.com','expertise.com','allpropertymanagement.com','narpm.org')
EXCLUDE=DIR_HOSTS+('facebook.com','linkedin.com','instagram.com','youtube.com','x.com','twitter.com','yelp.com','upwork.com','fiverr.com','google.com')
DIR_QUERIES=(
 'site:clutch.co/agencies digital marketing agencies United States',
 'site:clutch.co/agencies/seo SEO agencies United States',
 'site:clutch.co/hr/recruiting recruiting companies United States',
 'site:clutch.co/accounting accounting firms United States',
 'site:goodfirms.co digital marketing companies',
 'site:goodfirms.co business services staffing companies',
 'site:goodfirms.co business services accounting firms',
 'site:designrush.com agency digital marketing',
 'site:themanifest.com digital marketing companies',
 'site:agencyspotter.com marketing agencies',
 'site:sortlist.com marketing agencies',
 'site:allpropertymanagement.com property management companies',
 'site:narpm.org property managers',
)
SEGMENT_RULES={
 'marketing_agency':('marketing agency','digital agency','seo agency','ppc','paid media','creative agency','branding agency','performance marketing'),
 'recruiting':('recruiting','recruitment','staffing','executive search','talent acquisition'),
 'accounting':('accounting','bookkeeping','cpa','tax advisory','fractional cfo'),
 'property_management':('property management','property manager','tenant','rental management'),
 'b2b_services':('managed service provider','consulting firm','professional services','b2b services','outsourcing'),
}
BUYER=('founder','co-founder','ceo','owner','coo','managing director','head of operations','operations director')
STACK=('hubspot','salesforce','pipedrive','zoho','zapier','make.com','n8n','airtable','notion','crm','automation','artificial intelligence',' ai ')
GROWTH=('we are hiring','we’re hiring','careers','open roles','join our team','growing team','expanding','new office','multiple locations','our team','meet the team')
WORKLOAD=('reporting','follow-up','follow up','lead qualification','client onboarding','scheduling','data entry','admin','operations','workflow','inbox','document processing','research','prospecting','crm')
CAPACITY=('case studies','our clients','portfolio','trusted by','years of experience','locations','team of','employees')
CONTACT_HINTS=('contact','get-in-touch','get in touch','enquire','inquire','inquiry','enquiry','partnership','business-inquiries','general-inquiries')
BAD_ROUTE=('request-a-quote','get-a-quote','start-a-project','project-brief','work-with-us','hire-us','book-a-call','free-consult')
NO_SOLICIT=('no solicitation','no solicitations','no unsolicited','do not use this form for sales','no sales enquiries','no sales inquiries')

def host(u):
 try:
  h=urlparse(u).netloc.lower().split(':')[0]
  return h[4:] if h.startswith('www.') else h
 except:return ''

def segment(text):
 t=(text or '').lower(); best=('b2b_services',0)
 for k,words in SEGMENT_RULES.items():
  n=sum(1 for w in words if w in t)
  if n>best[1]: best=(k,n)
 return best[0]

def form_quality(url):
 p=(urlparse(url).path or '/').lower()
 if any(x in p for x in BAD_ROUTE): return 0
 if any(x in p for x in ('partnership','business-inquir','general-inquir')): return 20
 if p.rstrip('/').endswith(('contact','contact-us','get-in-touch','enquire','inquiry','enquiry')): return 15
 return 8

def cash_score(text,seg,form_url,form_found=True):
 t=' '+(text or '').lower()+' '; s=15
 s+=22 if any(x in t for x in BUYER) else 0
 s+=14 if any(x in t for x in GROWTH) else 0
 s+=14 if any(x in t for x in STACK) else 0
 s+=14 if any(x in t for x in WORKLOAD) else 0
 s+=10 if any(x in t for x in CAPACITY) else 0
 s+=8 if seg in ('marketing_agency','recruiting','accounting','property_management') else 3
 s+=form_quality(form_url) if form_found else 0
 return min(s,100)

def fetch(url,timeout=12):
 try:
  r=httpx.get(url,headers=UA,follow_redirects=True,timeout=timeout)
  if r.status_code<400 and 'html' in r.headers.get('content-type',''): return str(r.url),r.text
 except Exception: pass
 return None,None

def visible_text(html):
 if not html:return ''
 soup=BeautifulSoup(html,'lxml')
 for x in soup(['script','style','noscript']): x.decompose()
 return ' '.join(soup.stripped_strings)[:60000]

def has_form(html):
 if not html:return False
 low=html.lower()
 if any(x in low for x in NO_SOLICIT): return False
 soup=BeautifulSoup(html,'lxml')
 for f in soup.find_all('form'):
  fields=f.find_all(['input','textarea','select'])
  if any((x.name=='textarea' or (x.get('type') or '').lower() in ('text','email','tel')) for x in fields): return True
 return False

def find_form(base,html):
 if has_form(html): return base
 soup=BeautifulSoup(html or '','lxml'); cand=[]
 for a in soup.select('a[href]'):
  u=urljoin(base,a.get('href','')); h=(u+' '+a.get_text(' ',strip=True)).lower()
  if urlparse(u).netloc==urlparse(base).netloc and any(x in h for x in CONTACT_HINTS): cand.append(u)
 for p in ('/contact','/contact-us','/get-in-touch','/inquiry','/enquiry'):
  cand.append(urljoin(base,p))
 seen=set()
 for u in cand[:10]:
  if u in seen:continue
  seen.add(u); fu,fh=fetch(u)
  if fu and has_form(fh): return fu
 return ''

def load_existing():
 out={}
 if not DB.exists(): return out
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 q='''SELECT c.domain,c.homepage,c.country,f.page_url,f.status FROM companies c JOIN forms f ON f.company_id=c.id WHERE f.status='CONTACTABLE' GROUP BY c.domain ORDER BY c.id DESC LIMIT 20000'''
 try:
  for r in c.execute(q):
   d=(r['domain'] or '').lower(); u=r['homepage'] or ('https://'+d)
   if d and not any(x in d for x in EXCLUDE): out[d]={'domain':d,'website':u,'form_url':r['page_url'] or '', 'source':'existing_index','country':r['country'] or ''}
 finally:c.close()
 return out

def directory_seeds(max_pages=140):
 ddgs=DDGS(); pages=[]
 for q in DIR_QUERIES:
  try:
   for r in ddgs.text(q,max_results=12):
    u=r.get('href') or r.get('url') or ''
    if host(u) in DIR_HOSTS: pages.append((u,q))
  except Exception:pass
 pages=list(dict.fromkeys(pages))[:max_pages]; out={}
 def one(item):
  u,q=item; _,html=fetch(u)
  if not html:return []
  soup=BeautifulSoup(html,'lxml'); found=[]
  for a in soup.select('a[href]'):
   href=urljoin(u,a.get('href','')); d=host(href)
   if d and '.' in d and not any(x in d for x in EXCLUDE): found.append((d,href,q))
  return found
 with ThreadPoolExecutor(max_workers=16) as ex:
  for fut in as_completed([ex.submit(one,x) for x in pages]):
   try:
    for d,u,q in fut.result(): out.setdefault(d,{'domain':d,'website':'https://'+d,'form_url':'','source':'public_directory','country':'','directory_query':q})
   except Exception:pass
 return out

def qualify(item):
 base,html=fetch(item['website'])
 if not html:return None
 txt=visible_text(html); seg=segment(txt); f=item.get('form_url') or ''
 if not f: f=find_form(base,html)
 if not f:return None
 # Re-validate form even for legacy DB rows so stale/bad forms are removed.
 fu,fh=fetch(f)
 if not fu or not has_form(fh):return None
 evidence=txt[:2200]
 sc=cash_score(evidence,seg,fu,True)
 item.update({'website':base,'form_url':fu,'segment':seg,'score':sc,'evidence':evidence[:1200]})
 return item

pool=load_existing()
# Existing index is first-class; directories only expand the candidate universe.
if len(pool)<4000:
 for d,x in directory_seeds().items(): pool.setdefault(d,x)
print(json.dumps({'stage':'POOL','candidates':len(pool),'existing':sum(1 for x in pool.values() if x['source']=='existing_index')}),flush=True)

qualified=[]; items=list(pool.values())[:12000]
with ThreadPoolExecutor(max_workers=32) as ex:
 futs=[ex.submit(qualify,x) for x in items]
 for fut in as_completed(futs):
  try:
   x=fut.result()
   if x and x['score']>=55: qualified.append(x)
  except Exception:pass
ranked=sorted(qualified,key=lambda x:(x['score'],x['source']=='existing_index'),reverse=True)[:LIMIT]
for i,x in enumerate(ranked,1): x['rank']=i
fields=['rank','score','segment','domain','website','form_url','country','source','evidence']
with OUT.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(ranked)
OUTJ.write_text(json.dumps({'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'offer':'https://exior.io/ai-agent','count':len(ranked),'pool_size':len(pool),'prospects':ranked},indent=2),encoding='utf-8')
print(json.dumps({'status':'DONE','count':len(ranked),'pool':len(pool),'csv':str(OUT),'json':str(OUTJ),'top_score':ranked[0]['score'] if ranked else None}),flush=True)
