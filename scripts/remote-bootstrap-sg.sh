#!/bin/bash
set -euo pipefail
cd /opt/spider-radar
git fetch origin main && git reset --hard origin/main
. .venv/bin/activate
export PYTHONPATH=backend
cd backend
python scripts/seed_data.py 200

cat > /etc/systemd/system/spider-radar-api.service << 'UNIT'
[Unit]
Description=Spider Radar API
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/spider-radar/backend
EnvironmentFile=/opt/spider-radar/backend/.env
Environment=PYTHONPATH=/opt/spider-radar/backend
ExecStart=/opt/spider-radar/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 9092
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable spider-radar-api
systemctl restart spider-radar-api
sleep 2
curl -sf http://127.0.0.1:9092/health

cd /opt/spider-radar/frontend
npm ci
npm run build
mkdir -p /var/www/spider-radar
rm -rf /var/www/spider-radar/*
cp -r dist/* /var/www/spider-radar/

cat > /etc/nginx/sites-available/spider-radar << 'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/spider-radar;
    index index.html;
    location /api/ {
        proxy_pass http://127.0.0.1:9092/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/spider-radar /etc/nginx/sites-enabled/spider-radar
nginx -t && systemctl restart nginx
curl -sf http://127.0.0.1:9092/health
curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1/
echo
echo DEPLOY_OK
