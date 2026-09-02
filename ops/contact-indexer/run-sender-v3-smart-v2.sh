#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"

# Start from the latest proven SMART sender, then apply a deterministic hardening patch.
curl -fsSL "$RAW/sender-v3-smart.py" -o "$APP/sender-v3-smart-v2.py"

"$APP/venv-v3/bin/python" - "$APP/sender-v3-smart-v2.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')

# More alternate safe routes per company before giving up.
s=s.replace("MAX_ROUTES=int(os.getenv('MAX_ROUTES','5'))", "MAX_ROUTES=int(os.getenv('MAX_ROUTES','8'))")

# Verified contact identity. Phone is now a legitimate fill value rather than a rejection reason.
s=s.replace(
    "NAME='Guillaume'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; WEBSITE='https://exior.io/marketing-agencies/'",
    "FIRST_NAME='Guillaume'; LAST_NAME='Bauchart'; NAME='Guillaume Bauchart'; COMPANY='EXIOR'; EMAIL='contact@exior.io'; PHONE=os.getenv('CONTACT_PHONE','+33 7 55 71 99 59'); WEBSITE='https://exior.io/marketing-agencies/'"
)

# Broader but still conservative message-field vocabulary.
s=s.replace(
    "'what do you need','project details'",
    "'what do you need','project details','your request','your enquiry','your inquiry','additional information','additional details','comments or questions','how may we help','how can i help','tell us what','tell us how'"
)

# Required phone is no longer a negative form-quality signal because we can truthfully fill it.
s=s.replace(
    "if any(k=='phone' and m.get('required') for k,m in zip(kinds,metas)): score-=30",
    "if any(k=='phone' and m.get('required') for k,m in zip(kinds,metas)): score+=1"
)

# Fill truthful phone + first/last/full name intelligently.
s=s.replace(
    "if k=='email': await loc.fill(EMAIL)\n            elif k=='company': await loc.fill(COMPANY)\n            elif k=='website': await loc.fill(WEBSITE)\n            elif k=='name': await loc.fill(NAME)",
    "if k=='email': await loc.fill(EMAIL)\n            elif k=='phone': await loc.fill(PHONE)\n            elif k=='company': await loc.fill(COMPANY)\n            elif k=='website': await loc.fill(WEBSITE)\n            elif k=='name':\n                nt=' '.join(str(m.get(x) or '') for x in ('name','id','placeholder','aria','label','nearby')).lower()\n                if any(x in nt for x in ('last name','surname','family name')): await loc.fill(LAST_NAME)\n                elif any(x in nt for x in ('first name','given name','forename')): await loc.fill(FIRST_NAME)\n                else: await loc.fill(NAME)"
)

# Do not reject a live route simply because phone is required.
s=s.replace(
    "        if any(k=='phone' and m.get('required') for k,m in zip(kinds,metas)):\n            result.update(status='REQUIRED_PHONE',reason='required_phone_live'); return result\n",
    ""
)

# Required file fields cannot be fabricated: mark them unmapped before submit instead of wasting a click.
s=s.replace(
    "if typ in ('hidden','submit','button','file','image','reset','checkbox','radio'): continue",
    "if typ=='file':\n            if m.get('required'): required_unknown.append(m)\n            continue\n        if typ in ('hidden','submit','button','image','reset','checkbox','radio'): continue"
)

# Required select fields: only choose a clearly generic business-contact option; otherwise fail closed before click.
needle="""            elif k=='subject': await loc.fill(SUBJECT)\n            elif k=='message': await loc.fill(MESSAGE); message_ok=True\n            elif m.get('required') and (m.get('tag')!='select'): required_unknown.append(m)"""
replacement="""            elif k=='subject':\n                if m.get('tag')=='select':\n                    opts=await loc.locator('option').all()\n                    chosen=False\n                    for opt in opts:\n                        txt=((await opt.inner_text()) or '').strip().lower()\n                        val=(await opt.get_attribute('value')) or ''\n                        if val and any(x in txt for x in ('general','business','new business','other','enquiry','inquiry','contact')):\n                            await loc.select_option(value=val); chosen=True; break\n                    if not chosen and m.get('required'): required_unknown.append(m)\n                else: await loc.fill(SUBJECT)\n            elif k=='message': await loc.fill(MESSAGE); message_ok=True\n            elif m.get('tag')=='select' and m.get('required'):\n                opts=await loc.locator('option').all()\n                chosen=False\n                for opt in opts:\n                    txt=((await opt.inner_text()) or '').strip().lower()\n                    val=(await opt.get_attribute('value')) or ''\n                    if val and any(x in txt for x in ('general','business','new business','other','enquiry','inquiry','contact')):\n                        await loc.select_option(value=val); chosen=True; break\n                if not chosen: required_unknown.append(m)\n            elif m.get('required'): required_unknown.append(m)"""
s=s.replace(needle,replacement)

# A little more time for JS-rendered/embedded forms to finish mounting, without changing safety gates.
s=s.replace("await page.wait_for_timeout(1600)", "await page.wait_for_timeout(2400)")

p.write_text(s,encoding='utf-8')
print('SMART_V2_PATCHED', p)
PY

BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-8}"
MAX_ROUTES="${MAX_ROUTES:-8}"
CONTACT_PHONE="${CONTACT_PHONE:-+33 7 55 71 99 59}"

echo "Starting EXIOR SMART V2 sender: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES phone=$CONTACT_PHONE"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" CONTACT_PHONE="$CONTACT_PHONE" \
  "$APP/venv-v3/bin/python" "$APP/sender-v3-smart-v2.py" \
  >"$APP/logs/sender-smart-v2.log" 2>&1 &
echo $! > "$APP/logs/sender-smart-v2.pid"
echo "PID=$(cat "$APP/logs/sender-smart-v2.pid")"
echo "LOG=$APP/logs/sender-smart-v2.log"
