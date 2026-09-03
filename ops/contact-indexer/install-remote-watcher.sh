#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP/logs"
curl -fsSL "$RAW/remote-watcher.py?ts=$(date +%s)" -o "$APP/remote-watcher.py"
cat >/etc/systemd/system/exior-remote-watcher.service <<'UNIT'
[Unit]
Description=EXIOR Revenue OS GitHub Remote Batch Watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/usr/bin/python3 /opt/exior-contact-indexer/remote-watcher.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=REMOTE_POLL_SECONDS=20
MemoryMax=256M

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now exior-remote-watcher.service
sleep 2
systemctl --no-pager --full status exior-remote-watcher.service || true
echo '=== REMOTE CONTROL READY ==='
echo 'journalctl -u exior-remote-watcher -f'
