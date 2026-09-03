#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
mkdir -p "$APP/logs"
VENV="$APP/venv-browseruse"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

if [ ! -x "$PY" ]; then
  python3 -m venv "$VENV"
fi

export PIP_DEFAULT_TIMEOUT=180
export PIP_RETRIES=12

"$PIP" install --upgrade pip --timeout 180 --retries 12
"$PIP" install --timeout 180 --retries 12 --prefer-binary browser-use asyncpg httpx

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable --now ollama 2>/dev/null || true

if ! ollama list | grep -q '^llama3.1:8b'; then
  ollama pull llama3.1:8b
fi

"$PY" -m playwright install chromium || true
"$PY" - <<'PY'
import browser_use, asyncpg, httpx
print('V6_IMPORTS_OK')
PY

echo 'V6_BROWSERUSE_READY'
