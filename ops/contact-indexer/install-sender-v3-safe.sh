#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP"/{evidence,logs}
curl -fsSL "$RAW/sender-v3-safe.py" -o "$APP/sender-v3-safe.py"
if [ ! -x "$APP/venv-v3/bin/python" ]; then
  echo 'V3 venv missing; run install-v3.sh first' >&2
  exit 1
fi
"$APP/venv-v3/bin/pip" install -q asyncpg playwright
"$APP/venv-v3/bin/python" -m playwright install chromium >/dev/null 2>&1 || true
cat >/etc/systemd/system/exior-contact-sender-v3.service <<'UNIT'
[Unit]
Description=EXIOR guarded PostgreSQL V3 contact sender
After=network-online.target postgresql.service exior-contact-indexer-v3.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/opt/exior-contact-indexer/venv-v3/bin/python /opt/exior-contact-indexer/sender-v3-safe.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PG_DSN=postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact
Environment=SEND_WORKERS=2
Environment=MAX_PER_HOUR=20
MemoryMax=2G
LimitNOFILE=32768

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now exior-contact-sender-v3.service
sleep 4
systemctl --no-pager --full status exior-contact-sender-v3.service || true
journalctl -u exior-contact-sender-v3.service -n 30 --no-pager || true
