#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v4.py" -o "$APP/sender-v4.py"
curl -fsSL "$RAW/sender-v4-tolerant.py" -o "$APP/sender-v4-tolerant.py"
BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-8}"
MAX_ROUTES="${MAX_ROUTES:-8}"
echo "Starting EXIOR V4.1 tolerant sender: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" ENABLE_LOCAL_AI="${ENABLE_LOCAL_AI:-0}" \
  "$APP/venv-v4/bin/python" "$APP/sender-v4-tolerant.py" >"$APP/logs/sender-v4-tolerant.log" 2>&1 &
echo $! > "$APP/logs/sender-v4-tolerant.pid"
echo "PID=$(cat "$APP/logs/sender-v4-tolerant.pid")"
echo "LOG=$APP/logs/sender-v4-tolerant.log"
