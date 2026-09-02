#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer/sender-v3-batch-v2.py
BATCH_SIZE=${BATCH_SIZE:-100}
SEND_WORKERS=${SEND_WORKERS:-8}
mkdir -p "$APP/logs"
curl -fsSL "$RAW" -o "$APP/sender-v3-batch-v2.py"
echo "Starting EXIOR V3 batch sender v2: batch=$BATCH_SIZE workers=$SEND_WORKERS"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" "$APP/venv-v3/bin/python" "$APP/sender-v3-batch-v2.py" >"$APP/logs/sender-batch-v2.log" 2>&1 &
echo "PID=$!"
echo "LOG=$APP/logs/sender-batch-v2.log"
