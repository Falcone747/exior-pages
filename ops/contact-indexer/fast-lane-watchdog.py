#!/usr/bin/env python3
import json, os, signal, subprocess, time
from pathlib import Path

APP=Path('/opt/exior-contact-indexer')
STATE=APP/'fast-watchdog-state.json'
LOG=APP/'logs'/'fast-watchdog.log'
STALE_SECONDS=int(os.getenv('FAST_STALE_SECONDS','600'))
NO_PROGRESS_LIMIT=int(os.getenv('FAST_NO_PROGRESS_LIMIT','3'))

APP.mkdir(parents=True, exist_ok=True); (APP/'logs').mkdir(parents=True, exist_ok=True)

def log(msg):
    line=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+' '+msg
    print(line, flush=True)
    with LOG.open('a',encoding='utf-8') as f: f.write(line+'\n')

def sql(q):
    p=subprocess.run(['sudo','-u','postgres','psql','-d','exior_contact','-Atqc',q],capture_output=True,text=True,timeout=30)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip()[:500])
    return p.stdout.strip()

def count(q):
    s=sql(q)
    try: return int(s.splitlines()[-1]) if s else 0
    except: return 0

def pids():
    p=subprocess.run(['pgrep','-f',str(APP/'sender-v5-intelligent.py')],capture_output=True,text=True)
    return [int(x) for x in p.stdout.split() if x.isdigit()]

def kill_senders():
    ids=pids()
    for pid in ids:
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
    if ids:
        time.sleep(5)
        for pid in ids:
            try: os.kill(pid, 0); os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
    return ids

def load_state():
    try: return json.loads(STATE.read_text())
    except: return {'last_positive':0,'no_progress':0}

def save_state(s):
    tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(s,indent=2)); tmp.replace(STATE)

def main():
    st=load_state()
    positive=count("SELECT count(*) FROM submissions_v3 WHERE status IN ('SUCCESS_CONFIRMED','SUBMIT_ACCEPTED');")
    sending=count("SELECT count(*) FROM outreach_queue WHERE status='SENDING';")
    stale=count(f"SELECT count(*) FROM outreach_queue WHERE status='SENDING' AND updated_at < now() - interval '{STALE_SECONDS} seconds';")
    ready=count("SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY';")
    running=len(pids())

    if sending>0 and running>0 and positive<=int(st.get('last_positive',0)):
        st['no_progress']=int(st.get('no_progress',0))+1
    else:
        st['no_progress']=0

    # Hard recovery: stale DB claims or active sender with repeated zero progress.
    if stale>0 or (sending>0 and running>0 and st['no_progress']>=NO_PROGRESS_LIMIT):
        why=f'stale={stale}' if stale>0 else f'no_progress_checks={st["no_progress"]}'
        killed=kill_senders()
        requeued=count(f"WITH x AS (UPDATE outreach_queue SET status='MESSAGE_READY', updated_at=now() WHERE status='SENDING' AND updated_at < now() - interval '{STALE_SECONDS} seconds' RETURNING 1) SELECT count(*) FROM x;")
        # If process was killed for no-progress but timestamps were fresh, release all its SENDING claims.
        if requeued==0 and killed:
            requeued=count("WITH x AS (UPDATE outreach_queue SET status='MESSAGE_READY', updated_at=now() WHERE status='SENDING' RETURNING 1) SELECT count(*) FROM x;")
        log(f'RECOVER reason={why} killed={killed} requeued={requeued} positive={positive} ready_before={ready}')
        st['no_progress']=0
    else:
        log(f'HEALTH positive={positive} sending={sending} ready={ready} stale={stale} senders={running} no_progress={st["no_progress"]}')

    st['last_positive']=positive
    st['checked_at']=time.time()
    save_state(st)

if __name__=='__main__':
    try: main()
    except Exception as e: log('ERROR '+type(e).__name__+': '+str(e)[:500])
