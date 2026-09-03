#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
mkdir -p "$APP/logs"
PY="$APP/venv-browseruse/bin/python"
if [ ! -x "$PY" ]; then
  python3 -m venv "$APP/venv-browseruse"
  "$APP/venv-browseruse/bin/pip" install --upgrade pip
  "$APP/venv-browseruse/bin/pip" install browser-use asyncpg httpx
fi
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable --now ollama 2>/dev/null || true
ollama pull llama3.1:8b
"$APP/venv-browseruse/bin/python" -m playwright install chromium || true
echo 'V6_BROWSERUSE_READY'
