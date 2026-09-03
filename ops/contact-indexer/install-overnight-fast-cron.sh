#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RUNNER="$APP/run-fast-cron-once.sh"
STOP_FILE="$APP/overnight-fast-cron.stop-at"
LOG="$APP/logs/overnight-fast-cron.log"

mkdir -p "$APP/logs"
curl -fsSL "https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer/run-fast-cron-once.sh?ts=$(date +%s)" -o "$RUNNER"
chmod +x "$RUNNER"

date -d '+8 hours' +%s > "$STOP_FILE"

TMP=$(mktemp)
crontab -l 2>/dev/null | grep -v 'run-fast-cron-once.sh' > "$TMP" || true
printf '%s\n' '*/30 * * * * /opt/exior-contact-indexer/run-fast-cron-once.sh' >> "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "$(date -u +%FT%TZ) INSTALLED every_30m stop_at=$(cat "$STOP_FILE")" >> "$LOG"
"$RUNNER" || true

echo 'OVERNIGHT FAST CRON READY'
echo 'Schedule: every 30 minutes'
echo 'Batch: up to 100 MESSAGE_READY'
echo 'Workers: 6'
echo 'Overlap guard: enabled'
echo 'Auto-expiry: 8 hours'
