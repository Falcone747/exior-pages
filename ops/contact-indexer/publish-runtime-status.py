#!/usr/bin/env python3
import json, os, subprocess, time
from pathlib import Path

APP=Path('/opt/exior-contact-indexer')
REPO=Path('/opt/exior-telemetry')
REMOTE='git@github.com:Falcone747/exior-pages.git'
BRANCH='telemetry'
OUT='runtime-status.json'


def sh(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)

def psql(sql):
    r=sh(['sudo','-u','postgres','psql','-d','exior_contact','-At','-F','\t','-c',sql])
    return r.stdout.strip().splitlines() if r.stdout.strip() else []

def collect():
    status_counts={}
    for line in psql("SELECT status,count(*) FROM submissions_v3 GROUP BY status ORDER BY status"):
        s,n=line.split('\t',1); status_counts[s]=int(n)
    queue_counts={}
    for line in psql("SELECT status,count(*) FROM outreach_queue GROUP BY status ORDER BY status"):
        s,n=line.split('\t',1); queue_counts[s]=int(n)
    companies=[]
    q="""
    SELECT c.domain,s.status,COALESCE(s.form_url,'')
    FROM submissions_v3 s
    JOIN companies c ON c.id=s.company_id
    WHERE s.status IN ('SUCCESS_CONFIRMED','SUBMIT_ACCEPTED')
    ORDER BY s.created_at DESC NULLS LAST, c.domain
    LIMIT 500;
    """
    for line in psql(q):
        parts=line.split('\t')
        if len(parts)>=2:
            companies.append({'domain':parts[0],'status':parts[1],'form_url':parts[2] if len(parts)>2 else ''})
    smart_counts={}
    try:
        for line in psql("SELECT status,count(*) FROM browseruse_attempts_v6 GROUP BY status ORDER BY status"):
            s,n=line.split('\t',1); smart_counts[s]=int(n)
    except Exception:
        pass
    return {
        'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'submissions':status_counts,
        'queue':queue_counts,
        'smart':smart_counts,
        'totals':{
            'success_confirmed':status_counts.get('SUCCESS_CONFIRMED',0),
            'submit_accepted':status_counts.get('SUBMIT_ACCEPTED',0),
            'confirmed_or_accepted':status_counts.get('SUCCESS_CONFIRMED',0)+status_counts.get('SUBMIT_ACCEPTED',0),
            'sending':queue_counts.get('SENDING',0),
            'ready':queue_counts.get('MESSAGE_READY',0),
            'deferred':queue_counts.get('DEFERRED_PRECHECK',0),
        },
        'confirmed_companies':companies,
    }

def ensure_repo():
    if not (REPO/'.git').exists():
        if REPO.exists(): sh(['rm','-rf',str(REPO)])
        sh(['git','clone','--branch',BRANCH,'--single-branch',REMOTE,str(REPO)])
    sh(['git','fetch','origin',BRANCH],cwd=REPO)
    sh(['git','checkout',BRANCH],cwd=REPO)
    sh(['git','reset','--hard',f'origin/{BRANCH}'],cwd=REPO)
    sh(['git','config','user.name','EXIOR VPS Telemetry'],cwd=REPO)
    sh(['git','config','user.email','telemetry@exior.local'],cwd=REPO)

def publish():
    ensure_repo()
    data=collect()
    (REPO/OUT).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    sh(['git','add',OUT],cwd=REPO)
    diff=sh(['git','diff','--cached','--quiet'],cwd=REPO,check=False)
    if diff.returncode==0:
        return 'NO_CHANGE'
    sh(['git','commit','-m',f"telemetry {data['generated_at']}"] ,cwd=REPO)
    sh(['git','push','origin',BRANCH],cwd=REPO)
    return 'PUBLISHED'

if __name__=='__main__':
    try:
        print(publish())
    except Exception as e:
        print('ERROR',type(e).__name__,str(e)[:1000])
        raise
