#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v6-browseruse-fixed.py" -o "$APP/sender-v6-browseruse-fixed.py"
PY="$APP/venv-browseruse/bin/python"
if [ ! -x "$PY" ]; then echo "ERROR missing Browser Use venv" >&2; exit 1; fi
BATCH_SIZE="${BATCH_SIZE:-3}"
SMART_WORKERS="${SMART_WORKERS:-1}"
BROWSER_USE_MODEL="${BROWSER_USE_MODEL:-llama3.1:8b}"
echo "Starting V6 Browser Use minimal lane: batch=$BATCH_SIZE workers=$SMART_WORKERS model=$BROWSER_USE_MODEL"
nohup env BATCH_SIZE="$BATCH_SIZE" SMART_WORKERS="$SMART_WORKERS" BROWSER_USE_MODEL="$BROWSER_USE_MODEL" BROWSER_USE_DISABLE_EXTENSIONS=1 \
  "$PY" "$APP/sender-v6-browseruse-fixed.py" >"$APP/logs/sender-v6-browseruse-minimal.log" 2>&1 &
echo $! > "$APP/logs/sender-v6-browseruse-minimal.pid"
sleep 2
PID=$(cat "$APP/logs/sender-v6-browseruse-minimal.pid")
kill -0 "$PID" 2>/dev/null || { tail -100 "$APP/logs/sender-v6-browseruse-minimal.log"; exit 1; }
echo "PID=$PID"
echo "LOG=$APP/logs/sender-v6-browseruse-minimal.log"
