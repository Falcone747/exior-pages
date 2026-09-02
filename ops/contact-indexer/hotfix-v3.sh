#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
URL="https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer/v3_engine.py?nocache=$(date +%s)"
TMP="$APP/v3_engine.py.new"

echo '=== STOP V3 ==='
systemctl stop exior-contact-indexer-v3.service || true

curl -fL --retry 3 --retry-delay 1 "$URL" -o "$TMP"

echo '=== VERIFY HOTFIX ==='
grep -Fq '$7::jsonb' "$TMP" || { echo 'HOTFIX_FAIL: JSONB FIX MISSING'; exit 20; }
grep -Fq "str(e)[:160]" "$TMP" || { echo 'HOTFIX_FAIL: DETAILED ERROR LOG MISSING'; exit 21; }
grep -Fq 'http2=False' "$TMP" || { echo 'HOTFIX_FAIL: HTTP2 STILL ENABLED'; exit 22; }
"$APP/venv-v3/bin/python" -m py_compile "$TMP"
echo 'HOTFIX_CODE_VERIFIED'

mv "$TMP" "$APP/v3_engine.py"
chown root:root "$APP/v3_engine.py"

# Jobs abandoned by earlier crashing processes are safe to resolve again; no form submission happens in V3.
sudo -u postgres psql -d exior_contact -qAtc "UPDATE companies SET status='DISCOVERED', updated_at=now() WHERE status='RESOLVING';" >/dev/null

systemctl reset-failed exior-contact-indexer-v3.service || true
systemctl start exior-contact-indexer-v3.service
sleep 8

echo '=== ACTIVE CODE ==='
grep -nF '$7::jsonb' "$APP/v3_engine.py" | head -1
grep -nF "str(e)[:160]" "$APP/v3_engine.py" | head -1
grep -nF 'http2=False' "$APP/v3_engine.py" | head -1

echo '=== SERVICE ==='
systemctl is-active exior-contact-indexer-v3.service

echo '=== DB ==='
sudo -u postgres psql -d exior_contact -qAtc "SELECT 'companies='||count(*) FROM companies; SELECT 'forms='||count(*) FROM forms; SELECT 'contactable='||count(*) FROM forms WHERE status='CONTACTABLE'; SELECT 'ready='||count(*) FROM outreach_queue WHERE status='MESSAGE_READY';"

echo '=== LAST LOGS ==='
journalctl -u exior-contact-indexer-v3.service --since '-15 seconds' -n 30 --no-pager
