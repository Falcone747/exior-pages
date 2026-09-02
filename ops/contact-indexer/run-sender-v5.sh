#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v5-intelligent.py" -o "$APP/sender-v5-intelligent.py"
BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-4}"
MAX_ROUTES="${MAX_ROUTES:-8}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:1.7b}"
echo "Starting EXIOR V5 intelligent sender: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES model=$OLLAMA_MODEL"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" ENABLE_LOCAL_AI=1 OLLAMA_MODEL="$OLLAMA_MODEL" \
  "$APP/venv-v4/bin/python" "$APP/sender-v5-intelligent.py" \
  >"$APP/logs/sender-v5.log" 2>&1 &
echo $! > "$APP/logs/sender-v5.pid"
echo "PID=$(cat "$APP/logs/sender-v5.pid")"
echo "LOG=$APP/logs/sender-v5.log"
