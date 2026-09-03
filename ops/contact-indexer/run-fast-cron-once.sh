#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
LOG="$APP/logs/overnight-fast-cron.log"
LOCK=/tmp/exior-fast-cron.lock
STOP_FILE="$APP/overnight-fast-cron.stop-at"
NOW=$(date +%s)

mkdir -p "$APP/logs"

if [[ -f "$STOP_FILE" ]]; then
  STOP_AT=$(cat "$STOP_FILE" 2>/dev/null || echo 0)
  if [[ "$NOW" -ge "$STOP_AT" ]]; then
    echo "$(date -u +%FT%TZ) EXPIRED stop_at=$STOP_AT" >> "$LOG"
    crontab -l 2>/dev/null | grep -v 'run-fast-cron-once.sh' | crontab - || true
    exit 0
  fi
fi

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u +%FT%TZ) SKIP overlap lock_busy" >> "$LOG"
  exit 0
fi

if pgrep -f "$APP/sender-v5-intelligent.py" >/dev/null 2>&1; then
  echo "$(date -u +%FT%TZ) SKIP sender_already_running" >> "$LOG"
  exit 0
fi

READY=$(sudo -u postgres psql -d exior_contact -Atqc "SELECT count(*) FROM outreach_queue WHERE status='MESSAGE_READY';" 2>/dev/null || echo 0)
if [[ "${READY:-0}" -le 0 ]]; then
  echo "$(date -u +%FT%TZ) SKIP no_ready" >> "$LOG"
  exit 0
fi

BATCH=100
if [[ "$READY" -lt 100 ]]; then BATCH="$READY"; fi

echo "$(date -u +%FT%TZ) START batch=$BATCH ready=$READY" >> "$LOG"
nohup env BATCH_SIZE="$BATCH" SEND_WORKERS=6 MAX_ROUTES=8 ENABLE_LOCAL_AI=1 OLLAMA_MODEL=qwen3:1.7b \
  "$APP/venv-v3/bin/python" "$APP/sender-v5-intelligent.py" \
  >>"$LOG" 2>&1 &
echo "$(date -u +%FT%TZ) PID=$!" >> "$LOG"
