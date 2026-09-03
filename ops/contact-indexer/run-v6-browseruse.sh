#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v6-browseruse.py" -o "$APP/sender-v6-browseruse.py"
PY="$APP/venv-browseruse/bin/python"
if [ ! -x "$PY" ]; then echo "ERROR missing Browser Use venv; run install-v6-browseruse.sh" >&2; exit 1; fi
BATCH_SIZE="${BATCH_SIZE:-20}"
SMART_WORKERS="${SMART_WORKERS:-1}"
BROWSER_USE_MODEL="${BROWSER_USE_MODEL:-llama3.1:8b}"
echo "Starting V6 Browser Use lane: deferred_batch=$BATCH_SIZE workers=$SMART_WORKERS model=$BROWSER_USE_MODEL"
nohup env BATCH_SIZE="$BATCH_SIZE" SMART_WORKERS="$SMART_WORKERS" BROWSER_USE_MODEL="$BROWSER_USE_MODEL" \
  "$PY" "$APP/sender-v6-browseruse.py" >"$APP/logs/sender-v6-browseruse.log" 2>&1 &
echo $! > "$APP/logs/sender-v6-browseruse.pid"
sleep 2
PID=$(cat "$APP/logs/sender-v6-browseruse.pid")
kill -0 "$PID" 2>/dev/null || { tail -100 "$APP/logs/sender-v6-browseruse.log"; exit 1; }
echo "PID=$PID"
echo "LOG=$APP/logs/sender-v6-browseruse.log"
