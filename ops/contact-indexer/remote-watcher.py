import json, os, subprocess, time, urllib.request
from pathlib import Path
APP=Path('/opt/exior-contact-indexer')
RAW='https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer'
CONTROL_URL=RAW+'/remote-control.json'; STATE=APP/'remote-control.state.json'; LOG=APP/'logs'/'remote-control.log'; POLL=int(os.getenv('REMOTE_POLL_SECONDS','20'))
APP.mkdir(parents=True,exist_ok=True); (APP/'logs').mkdir(parents=True,exist_ok=True)
def log(msg):
 line=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+' '+msg; print(line,flush=True)
 with LOG.open('a',encoding='utf-8') as f:f.write(line+'\n')
def load_state():
 try:return json.loads(STATE.read_text())
 except:return {'last_command_id':None}
def save_state(s):
 tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(s,indent=2)); tmp.replace(STATE)
def fetch_control():
 req=urllib.request.Request(CONTROL_URL+'?t='+str(int(time.time())),headers={'Cache-Control':'no-cache','User-Agent':'EXIOR-remote-watcher'})
 with urllib.request.urlopen(req,timeout=10) as r:return json.loads(r.read().decode())
def detached(py,script,env,logfile):
 out=open(logfile,'ab',buffering=0); p=subprocess.Popen([str(py),str(script)],stdout=out,stderr=subprocess.STDOUT,start_new_session=True,cwd=str(APP),env=env); return p.pid
def execute(c):
 action=str(c.get('action','idle')).lower()
 if action=='idle': return {'status':'IDLE'}
 if action=='prospect_build':
  script=APP/'prospect-builder-ai-agent.py'; urllib.request.urlretrieve(RAW+'/prospect-builder-ai-agent.py?ts='+str(int(time.time())),script)
  py=APP/'venv-v3'/'bin'/'python'; env=os.environ.copy(); env['PROSPECT_LIMIT']=str(max(50,min(int(c.get('limit',500)),500)))
  logfile=APP/'logs'/f"prospect-build-{c['command_id']}.log"; pid=detached(py,script,env,logfile)
  return {'status':'STARTED','mode':'prospect_build','pid':pid,'log':str(logfile),'limit':env['PROSPECT_LIMIT'],'output':str(APP/'data'/'ai-agent-top-500.csv')}
 if action!='batch': return {'status':'IGNORED','reason':'unknown_action'}
 mode=str(c.get('mode','fast')).lower(); batch=max(1,min(int(c.get('batch_size',100)),500)); workers=max(1,min(int(c.get('workers',4)),12)); routes=max(1,min(int(c.get('max_routes',8)),12))
 if mode=='fast':
  py=APP/'venv-v3'/'bin'/'python'; script=APP/'sender-v5-intelligent.py'
  if not script.exists(): urllib.request.urlretrieve(RAW+'/sender-v5-intelligent.py',script)
  env=os.environ.copy(); env.update(BATCH_SIZE=str(batch),SEND_WORKERS=str(workers),MAX_ROUTES=str(routes),ENABLE_LOCAL_AI='1',OLLAMA_MODEL=str(c.get('model','qwen3:1.7b')))
  logfile=APP/'logs'/f"remote-fast-{c['command_id']}.log"; pid=detached(py,script,env,logfile); return {'status':'STARTED','mode':'fast','pid':pid,'log':str(logfile),'batch_size':batch,'workers':workers}
 if mode in ('smart','browseruse'):
  py=APP/'venv-browseruse'/'bin'/'python'; script=APP/'sender-v6-browseruse-fixed.py'
  if not script.exists(): urllib.request.urlretrieve(RAW+'/sender-v6-browseruse-fixed.py',script)
  env=os.environ.copy(); env.update(BATCH_SIZE=str(batch),SMART_WORKERS=str(min(workers,2)),BROWSER_USE_MODEL=str(c.get('model','llama3.1:8b')),BROWSER_USE_DISABLE_EXTENSIONS='1')
  logfile=APP/'logs'/f"remote-smart-{c['command_id']}.log"; pid=detached(py,script,env,logfile); return {'status':'STARTED','mode':'smart','pid':pid,'log':str(logfile),'batch_size':batch,'workers':min(workers,2)}
 return {'status':'IGNORED','reason':'unknown_mode'}
def main():
 state=load_state(); log('REMOTE_WATCHER_STARTED poll='+str(POLL))
 while True:
  try:
   c=fetch_control(); cid=str(c.get('command_id',''))
   if cid and cid!=state.get('last_command_id'):
    result=execute(c); state={'last_command_id':cid,'last_control':c,'last_result':result,'processed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}; save_state(state); log('COMMAND '+cid+' '+json.dumps(result,separators=(',',':')))
  except Exception as e: log('ERROR '+type(e).__name__+':'+str(e)[:300])
  time.sleep(POLL)
if __name__=='__main__': main()
