#!/usr/bin/env bash
set -euo pipefail
APP=/opt/exior-contact-indexer
RAW=https://raw.githubusercontent.com/Falcone747/exior-pages/main/ops/contact-indexer
mkdir -p "$APP"/{data,evidence,logs}
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip curl ca-certificates \
  postgresql postgresql-contrib redis-server \
  libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 fonts-liberation
systemctl enable --now postgresql redis-server
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='exior'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER exior WITH PASSWORD 'exior_local_only';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='exior_contact'" | grep -q 1 || sudo -u postgres createdb -O exior exior_contact
curl -fsSL "$RAW/v3_engine.py" -o "$APP/v3_engine.py"
curl -fsSL "$RAW/requirements-v3.txt" -o "$APP/requirements-v3.txt"
systemctl stop exior-contact-indexer-v3.service 2>/dev/null || true
rm -rf "$APP/venv-v3"
python3 -m venv "$APP/venv-v3"
"$APP/venv-v3/bin/pip" install --upgrade pip
"$APP/venv-v3/bin/pip" install -r "$APP/requirements-v3.txt"
"$APP/venv-v3/bin/pip" install 'h2>=4.1,<5'
"$APP/venv-v3/bin/python" -c "import h2,httpx; print('HTTP2_DEPS_OK', h2.__version__, httpx.__version__)"
"$APP/venv-v3/bin/python" -m playwright install chromium
cat >/etc/systemd/system/exior-contact-indexer-v3.service <<'UNIT'
[Unit]
Description=EXIOR Contact Indexer V3 PostgreSQL Redis
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/exior-contact-indexer
ExecStart=/opt/exior-contact-indexer/venv-v3/bin/python /opt/exior-contact-indexer/v3_engine.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=PG_DSN=postgresql://exior:exior_local_only@127.0.0.1:5432/exior_contact
Environment=REDIS_URL=redis://127.0.0.1:6379/0
Environment=HTTP_CONCURRENCY=200
Environment=DISCOVERY_WORKERS=20
Environment=RESOLVER_WORKERS=12
Environment=SCREENSHOT_WORKERS=6
Environment=CITY_MIN_POP=25000
MemoryMax=7G
LimitNOFILE=65535
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl stop exior-contact-indexer.service 2>/dev/null || true
systemctl enable exior-contact-indexer-v3.service
systemctl restart exior-contact-indexer-v3.service
sleep 8
echo '=== V3 STATUS ==='
systemctl --no-pager --full status exior-contact-indexer-v3.service || true
echo '=== V3 LOGS ==='
journalctl -u exior-contact-indexer-v3.service -n 40 --no-pager || true
echo '=== COMMAND ==='
echo 'journalctl -u exior-contact-indexer-v3 -f'
