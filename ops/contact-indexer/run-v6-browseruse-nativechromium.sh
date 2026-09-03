#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"

curl -fsSL "$RAW/sender-v6-browseruse-fixed.py" -o "$APP/sender-v6-browseruse-fixed.py"
curl -fsSL "$RAW/sender-v6-browseruse-nativechromium.py" -o "$APP/sender-v6-browseruse-nativechromium.py"

# Discover the exact Chromium binary already installed and successfully used by Playwright V3.
CHROMIUM_EXECUTABLE="$($APP/venv-v3/bin/python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    print(p.chromium.executable_path)
PY
)"
[ -x "$CHROMIUM_EXECUTABLE" ] || { echo "ERROR chromium not executable: $CHROMIUM_EXECUTABLE" >&2; exit 1; }

# Requeue only Browser Use integration errors; these failed before submission.
sudo -u postgres psql -d exior_contact -v ON_ERROR_STOP=1 -q -c "
UPDATE outreach_queue q SET status='DEFERRED_PRECHECK',updated_at=now()
FROM browseruse_attempts_v6 a
WHERE q.company_id=a.company_id AND a.status='SMART_ERROR';
" >/dev/null

BATCH_SIZE="${BATCH_SIZE:-3}"
SMART_WORKERS="${SMART_WORKERS:-1}"
BROWSER_USE_MODEL="${BROWSER_USE_MODEL:-llama3.1:8b}"
LOG="$APP/logs/sender-v6-nativechromium.log"

echo "Starting native Chromium Browser Use: batch=$BATCH_SIZE workers=$SMART_WORKERS model=$BROWSER_USE_MODEL chromium=$CHROMIUM_EXECUTABLE"
nohup env BROWSER_USE_DISABLE_EXTENSIONS=1 BROWSER_USE_HEADLESS=1 CHROMIUM_EXECUTABLE="$CHROMIUM_EXECUTABLE" BATCH_SIZE="$BATCH_SIZE" SMART_WORKERS="$SMART_WORKERS" BROWSER_USE_MODEL="$BROWSER_USE_MODEL" \
  "$APP/venv-browseruse/bin/python" "$APP/sender-v6-browseruse-nativechromium.py" >"$LOG" 2>&1 &
echo $! > "$APP/logs/sender-v6-nativechromium.pid"
echo "PID=$(cat "$APP/logs/sender-v6-nativechromium.pid")"
echo "LOG=$LOG"
