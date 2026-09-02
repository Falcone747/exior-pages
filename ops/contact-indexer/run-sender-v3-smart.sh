#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v3-smart.py" -o "$APP/sender-v3-smart.py"
BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-8}"
MAX_ROUTES="${MAX_ROUTES:-5}"
echo "Starting EXIOR SMART V3 sender: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" \
  "$APP/venv-v3/bin/python" "$APP/sender-v3-smart.py" \
  >"$APP/logs/sender-smart.log" 2>&1 &
echo $! > "$APP/logs/sender-smart.pid"
echo "PID=$(cat "$APP/logs/sender-smart.pid")"
echo "LOG=$APP/logs/sender-smart.log"
