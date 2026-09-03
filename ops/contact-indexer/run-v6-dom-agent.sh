#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/sender-v6-dom-agent.py" -o "$APP/sender-v6-dom-agent.py"
PY="$APP/venv-v3/bin/python"
BATCH_SIZE="${BATCH_SIZE:-50}"
SEND_WORKERS="${SEND_WORKERS:-2}"
MAX_ROUTES="${MAX_ROUTES:-8}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:1.7b}"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" OLLAMA_MODEL="$OLLAMA_MODEL" AI_TIMEOUT=35 \
  "$PY" "$APP/sender-v6-dom-agent.py" >"$APP/logs/sender-v6-dom.log" 2>&1 &
echo $! > "$APP/logs/sender-v6-dom.pid"
echo "V6_DOM_PID=$(cat "$APP/logs/sender-v6-dom.pid")"
echo "LOG=$APP/logs/sender-v6-dom.log"
