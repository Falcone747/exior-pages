#!/usr/bin/env bash
set -euo pipefail

ROOT=/opt/exior
RUNTIME="$ROOT/runtime"
REPO_URL="https://github.com/Falcone747/EXIOR-.git"
BRANCH="claude/session-setup-HTA1V"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Run as root" >&2
  exit 1
fi

if [ -z "${RUNPOD_API_KEY:-}" ]; then
  printf 'RunPod read-only API key: '
  stty -echo
  read -r RUNPOD_API_KEY
  stty echo
  printf '\n'
fi

# Pull only the runtime files through GitHub public mirror branch if present locally; otherwise use current runtime.
# The secret is persisted only in /opt/exior/runtime/.env (0600), never printed.
mkdir -p "$RUNTIME"
ENVFILE="$RUNTIME/.env"
if [ ! -f "$ENVFILE" ]; then
  touch "$ENVFILE"
fi
chmod 600 "$ENVFILE"

python3 - "$ENVFILE" "$RUNPOD_API_KEY" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); key=sys.argv[2]
lines=p.read_text().splitlines() if p.exists() else []
out=[]; seen=False
for line in lines:
    if line.startswith('RUNPOD_API_KEY='):
        out.append('RUNPOD_API_KEY='+key); seen=True
    else:
        out.append(line)
if not seen: out.append('RUNPOD_API_KEY='+key)
p.write_text('\n'.join(out)+'\n')
PY

# Existing EXIOR runtime remains the source of truth; restart services so the key is loaded.
cd "$RUNTIME"
docker compose up -d --build --force-recreate gpu-router litellm exior-worker

printf '\nEXIOR runtime updated.\n'
curl -fsS http://127.0.0.1:8001/health || true
printf '\n'
