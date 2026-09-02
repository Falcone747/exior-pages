#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
REPO=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP"/{data,evidence,logs}
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip curl ca-certificates sqlite3 libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 fonts-liberation
curl -fsSL "$REPO/engine.py" -o "$APP/engine.py"
curl -fsSL "$REPO/requirements.txt" -o "$APP/requirements.txt"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip
"$APP/venv/bin/pip" install -r "$APP/requirements.txt"
"$APP/venv/bin/python" -m playwright install --with-deps chromium
cat >/etc/systemd/system/exior-contact-indexer.service <<'UNIT'
[Unit]
Description=EXIOR Contact Form Indexer
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/opt/exior-contact-indexer/venv/bin/python /opt/exior-contact-indexer/engine.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=HTTP_CONCURRENCY=60
Environment=CITY_MIN_POP=25000
MemoryMax=6G
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now exior-contact-indexer.service
sleep 5
echo '=== SERVICE ==='
systemctl --no-pager --full status exior-contact-indexer.service || true
echo '=== LOGS ==='
journalctl -u exior-contact-indexer.service -n 30 --no-pager || true
echo '=== COMMANDS ==='
echo 'journalctl -u exior-contact-indexer -f'
echo "sqlite3 $APP/data/index.db \"select status,count(*) from companies group by status;\""
echo "sqlite3 $APP/data/index.db \"select status,count(*) from forms group by status;\""
