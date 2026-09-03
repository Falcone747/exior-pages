#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/publish-runtime-status.py?ts=$(date +%s)" -o "$APP/publish-runtime-status.py"
chmod +x "$APP/publish-runtime-status.py"
cat >/etc/systemd/system/exior-runtime-telemetry.service <<'EOF'
[Unit]
Description=EXIOR runtime telemetry publisher
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/exior-contact-indexer/publish-runtime-status.py
StandardOutput=append:/opt/exior-contact-indexer/logs/runtime-telemetry.log
StandardError=append:/opt/exior-contact-indexer/logs/runtime-telemetry.log
EOF
cat >/etc/systemd/system/exior-runtime-telemetry.timer <<'EOF'
[Unit]
Description=Publish EXIOR runtime telemetry every 2 minutes

[Timer]
OnBootSec=15s
OnUnitActiveSec=120s
AccuracySec=10s
Unit=exior-runtime-telemetry.service
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now exior-runtime-telemetry.timer
systemctl start exior-runtime-telemetry.service || true
sleep 2
echo '=== TIMER ==='
systemctl --no-pager --full status exior-runtime-telemetry.timer | sed -n '1,12p'
echo '=== LAST TELEMETRY ==='
tail -20 "$APP/logs/runtime-telemetry.log" 2>/dev/null || true
echo 'RUNTIME TELEMETRY READY'
