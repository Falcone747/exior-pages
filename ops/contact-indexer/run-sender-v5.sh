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
PY="$APP/venv-v3/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: missing $PY" >&2
  exit 1
fi
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "ERROR: Ollama is not reachable on 127.0.0.1:11434" >&2
  exit 1
fi
echo "Starting EXIOR V5 intelligent sender: batch=$BATCH_SIZE workers=$SEND_WORKERS routes=$MAX_ROUTES model=$OLLAMA_MODEL python=$PY"
nohup env BATCH_SIZE="$BATCH_SIZE" SEND_WORKERS="$SEND_WORKERS" MAX_ROUTES="$MAX_ROUTES" ENABLE_LOCAL_AI=1 OLLAMA_MODEL="$OLLAMA_MODEL" AI_TIMEOUT=20 \
  "$PY" "$APP/sender-v5-intelligent.py" \
  >"$APP/logs/sender-v5.log" 2>&1 &
echo $! > "$APP/logs/sender-v5.pid"
sleep 2
PID="$(cat "$APP/logs/sender-v5.pid")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "ERROR: V5 exited immediately" >&2
  tail -80 "$APP/logs/sender-v5.log" >&2 || true
  exit 1
fi
echo "PID=$PID"
echo "LOG=$APP/logs/sender-v5.log"
