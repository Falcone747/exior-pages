#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-8}"
mkdir -p "$APP"/{evidence,logs}
curl -fsSL "$RAW/sender-v3-batch.py" -o "$APP/sender-v3-batch.py"
if [ ! -x "$APP/venv-v3/bin/python" ]; then
  echo 'V3 venv missing: run install-v3.sh first' >&2
  exit 1
fi
# Never stop or restart the active discovery/resolver service.
# This is a one-shot bounded batch that shares PostgreSQL safely via SKIP LOCKED.
echo "Starting EXIOR V3 batch sender: batch=$BATCH_SIZE workers=$SEND_WORKERS"
PG_DSN='postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact' \
BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" \
"$APP/venv-v3/bin/python" "$APP/sender-v3-batch.py" | tee -a "$APP/logs/sender-v3-batch.log"
echo '=== POST-BATCH COUNTS ==='
PGPASSWORD=exior_local_only psql -h 127.0.0.1 -U exior -d exior_contact -Atc "SELECT 'ready='||count(*) FROM outreach_queue WHERE status='MESSAGE_READY'; SELECT status||'='||count(*) FROM submissions_v3 GROUP BY status ORDER BY status;" || true
