#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs" "$APP/evidence"

curl -fsSL "$RAW/sender-v4.py" -o "$APP/sender-v4.py"
curl -fsSL "$RAW/requirements-sender-v4.txt" -o "$APP/requirements-sender-v4.txt"

if [ ! -x "$APP/venv-sender-v4/bin/python" ]; then
  python3 -m venv "$APP/venv-sender-v4"
  "$APP/venv-sender-v4/bin/pip" install --upgrade pip
  "$APP/venv-sender-v4/bin/pip" install -r "$APP/requirements-sender-v4.txt"
  "$APP/venv-sender-v4/bin/python" -m playwright install chromium
fi

BATCH_SIZE="${BATCH_SIZE:-100}"
SEND_WORKERS="${SEND_WORKERS:-8}"
MAX_ROUTES="${MAX_ROUTES:-8}"
ENABLE_LOCAL_AI="${ENABLE_LOCAL_AI:-0}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:4b}"

echo "Starting EXIOR sender V4: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES local_ai=$ENABLE_LOCAL_AI"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" ENABLE_LOCAL_AI="$ENABLE_LOCAL_AI" OLLAMA_MODEL="$OLLAMA_MODEL" \
  "$APP/venv-sender-v4/bin/python" "$APP/sender-v4.py" \
  >"$APP/logs/sender-v4.log" 2>&1 &
echo $! > "$APP/logs/sender-v4.pid"
echo "PID=$(cat "$APP/logs/sender-v4.pid")"
echo "LOG=$APP/logs/sender-v4.log"
