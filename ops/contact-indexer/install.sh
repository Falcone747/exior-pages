#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
REPO=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP"/{data,evidence,logs}
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip curl ca-certificates sqlite3 libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 fonts-liberation
curl -fsSL "$REPO/engine.py" -o "$APP/engine.py"
curl -fsSL "$REPO/sender.py" -o "$APP/sender.py"
curl -fsSL "$REPO/requirements.txt" -o "$APP/requirements.txt"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip
"$APP/venv/bin/pip" install -r "$APP/requirements.txt"
"$APP/venv/bin/python" -m playwright install chromium
cat >/etc/systemd/system/exior-contact-indexer.service <<'UNIT'
[Unit]
Description=EXIOR Parallel Contact Form Indexer
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/opt/exior-contact-indexer/venv/bin/python /opt/exior-contact-indexer/engine.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=HTTP_CONCURRENCY=120
Environment=DISCOVERY_WORKERS=12
Environment=SCREENSHOT_WORKERS=8
Environment=CITY_MIN_POP=25000
MemoryMax=7G
[Install]
WantedBy=multi-user.target
UNIT
cat >/etc/systemd/system/exior-contact-sender.service <<'UNIT'
[Unit]
Description=EXIOR Evidence-backed Contact Sender
After=network-online.target exior-contact-indexer.service
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/opt/exior-contact-indexer/venv/bin/python /opt/exior-contact-indexer/sender.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=SEND_WORKERS=4
MemoryMax=4G
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable exior-contact-indexer.service exior-contact-sender.service
systemctl restart exior-contact-indexer.service
systemctl restart exior-contact-sender.service
sleep 6
echo '=== EXIOR INDEXER ==='
systemctl --no-pager --full status exior-contact-indexer.service || true
echo '=== EXIOR SENDER ==='
systemctl --no-pager --full status exior-contact-sender.service || true
echo '=== DATABASE ==='
sqlite3 "$APP/data/index.db" "SELECT 'companies',COUNT(*) FROM companies; SELECT 'forms',COUNT(*) FROM forms; SELECT 'message_ready',COUNT(*) FROM outreach_queue WHERE status='MESSAGE_READY'; SELECT status,COUNT(*) FROM submissions GROUP BY status;" || true
echo '=== LIVE ==='
echo 'journalctl -u exior-contact-indexer -f'
echo 'journalctl -u exior-contact-sender -f'
