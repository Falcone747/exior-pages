#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable --now ollama || true
sleep 2
ollama pull qwen3:1.7b
curl -fsSL "$RAW/sender-v5-intelligent.py" -o "$APP/sender-v5-intelligent.py"
echo 'V5 intelligence installed.'
echo 'Model:'
ollama list | grep -E '^qwen3:1.7b' || true
