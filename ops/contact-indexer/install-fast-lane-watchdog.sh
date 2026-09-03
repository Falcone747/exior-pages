#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
mkdir -p "$APP/logs"

curl -fsSL "https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer/fast-lane-watchdog.py?ts=$(date +%s)" -o "$APP/fast-lane-watchdog.py"
chmod +x "$APP/fast-lane-watchdog.py"

cat >/etc/systemd/system/exior-fast-watchdog.service <<'EOF'
[Unit]
Description=EXIOR Fast Lane self-healing watchdog
After=postgresql.service network-online.target

[Service]
Type=oneshot
Environment=FAST_STALE_SECONDS=600
Environment=FAST_NO_PROGRESS_LIMIT=3
ExecStart=/usr/bin/python3 /opt/exior-contact-indexer/fast-lane-watchdog.py
EOF

cat >/etc/systemd/system/exior-fast-watchdog.timer <<'EOF'
[Unit]
Description=Run EXIOR Fast Lane watchdog every 2 minutes

[Timer]
OnBootSec=60
OnUnitActiveSec=120
AccuracySec=15
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Refresh the cron runner so future batches get the current guarded version.
curl -fsSL "https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer/run-fast-cron-once.sh?ts=$(date +%s)" -o "$APP/run-fast-cron-once.sh"
chmod +x "$APP/run-fast-cron-once.sh"

systemctl daemon-reload
systemctl enable --now exior-fast-watchdog.timer
systemctl start exior-fast-watchdog.service || true

echo '=== FAST LANE WATCHDOG READY ==='
systemctl --no-pager --full status exior-fast-watchdog.timer | sed -n '1,12p'
tail -10 "$APP/logs/fast-watchdog.log" 2>/dev/null || true
