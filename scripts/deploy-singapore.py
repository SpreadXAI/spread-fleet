#!/usr/bin/env python3
"""Deploy Spider雷达 to Singapore ECS via Aliyun Cloud Assistant."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeInvocationResultsRequest, RunCommandRequest

ROOT = Path(__file__).resolve().parents[1]
REGION = "ap-southeast-1"
INSTANCE = os.environ.get("SPIDER_RADAR_INSTANCE", "i-t4n571mpi11mkib9ubxj")
TACTILE_INSTANCE = os.environ.get("TACTILE_DB_SOURCE_INSTANCE", "i-t4n30tqeuanmlmhswi5h")
API_PORT = 9092


def run_remote(region: str, instance_id: str, cmd: str, wait: int = 10, max_wait: int = 900) -> tuple[str, str]:
    client = AcsClient(os.environ["ALIYUN_ACCESS_KEY_ID"], os.environ["ALIYUN_ACCESS_KEY_SECRET"], region)
    req = RunCommandRequest.RunCommandRequest()
    req.set_InstanceIds([instance_id])
    req.set_CommandContent(cmd)
    req.set_Type("RunShellScript")
    req.set_accept_format("json")
    resp = json.loads(client.do_action_with_exception(req))
    invoke_id = resp["InvokeId"]
    elapsed = 0
    status = "Running"
    out = ""
    while elapsed < max_wait:
        time.sleep(wait)
        elapsed += wait
        req2 = DescribeInvocationResultsRequest.DescribeInvocationResultsRequest()
        req2.set_InvokeId(invoke_id)
        req2.set_accept_format("json")
        r2 = json.loads(client.do_action_with_exception(req2))
        for item in r2.get("Invocation", {}).get("InvocationResults", {}).get("InvocationResult", []):
            status = item.get("InvocationStatus", "")
            raw = item.get("Output", "")
            try:
                out = base64.b64decode(raw).decode()
            except Exception:
                out = raw
            if status in ("Success", "Failed", "Timeout", "Cancelled"):
                return status, out
    return status, out


def fetch_db_env() -> dict[str, str]:
    cmd = r"""#!/bin/bash
set -euo pipefail
test -f /etc/tactile/env
set -a
. /etc/tactile/env
set +a
printf 'HOST=%s\n' "${DF_DATABASE_HOST:-}"
printf 'USER=%s\n' "${DF_DATABASE_USER:-tactile_app}"
printf 'NAME=%s\n' "${TACTILE_DATABASE_NAME:-tactile}"
printf 'PASS=%s\n' "${DF_DATABASE_PASSWORD:-}"
"""
    status, out = run_remote(REGION, TACTILE_INSTANCE, cmd, wait=8, max_wait=120)
    if status != "Success":
        raise RuntimeError(f"Failed to read tactile DB env: {status}\n{out}")
    env: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    if not env.get("PASS") or not env.get("HOST"):
        raise RuntimeError("Missing database credentials from tactile env")
    return env


def build_bootstrap_script(jwt_secret: str, clone_url: str, db: dict[str, str]) -> str:
    def esc(s: str) -> str:
        return s.replace("'", "'\"'\"'")

    return f"""#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq git nginx python3 python3-venv python3-pip curl ca-certificates

if ! command -v node >/dev/null 2>&1 || [ "$(node -v | sed 's/v//' | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

REMOTE_DIR=/opt/spider-radar
WEB_DIR=/var/www/spider-radar
SERVICE=spider-radar-api
CLONE_URL='{esc(clone_url)}'

mkdir -p "$REMOTE_DIR" "$WEB_DIR"
if [ -d "$REMOTE_DIR/.git" ]; then
  cd "$REMOTE_DIR" && git remote set-url origin "$CLONE_URL" && git fetch origin main && git reset --hard origin/main
else
  git clone "$CLONE_URL" "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"

python3 -m venv .venv
. .venv/bin/activate
pip install -q -r backend/requirements.txt

cat > backend/.env << EOF
ENVIRONMENT=production
DATABASE_HOST={esc(db["HOST"])}
DATABASE_USER={esc(db.get("USER", "tactile_app"))}
DATABASE_NAME={esc(db.get("NAME", "tactile"))}
DATABASE_PASSWORD={esc(db["PASS"])}
JWT_SECRET={esc(jwt_secret)}
EOF

export PYTHONPATH=backend
cd backend
python -c "from app.database import ensure_schema; from app.models import Base; from app.database import engine; ensure_schema(); Base.metadata.create_all(bind=engine)"
python scripts/migrate_schema.py
python scripts/seed_data.py 200
cd "$REMOTE_DIR"

cat > /etc/systemd/system/$SERVICE.service << 'UNIT'
[Unit]
Description=Spider Radar API
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/spider-radar/backend
EnvironmentFile=/opt/spider-radar/backend/.env
Environment=PYTHONPATH=/opt/spider-radar/backend
ExecStart=/opt/spider-radar/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port {API_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable $SERVICE
systemctl restart $SERVICE
sleep 3
curl -sf http://127.0.0.1:{API_PORT}/health

cd "$REMOTE_DIR/frontend"
npm ci
npm run build
rm -rf "$WEB_DIR"/*
cp -r dist/* "$WEB_DIR/"

cat > /etc/nginx/sites-available/spider-radar << NGINX
server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/spider-radar;
    index index.html;

    location /api/ {{
        proxy_pass http://127.0.0.1:{API_PORT}/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
    }}

    location / {{
        try_files \$uri \$uri/ /index.html;
    }}
}}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/spider-radar /etc/nginx/sites-enabled/spider-radar
nginx -t
systemctl enable nginx
systemctl restart nginx

curl -sf http://127.0.0.1/health || curl -sf http://127.0.0.1:{API_PORT}/health
curl -sf -o /dev/null -w "%{{http_code}}" http://127.0.0.1/
echo
echo DEPLOY_OK
"""


def main() -> None:
    jwt_secret = os.environ.get("JWT_SECRET", "spider-radar-prod-jwt-secret-4918")
    gh_token = os.environ.get("github_access_token") or os.environ.get("GH_TOKEN", "")

    print("==> Push latest to GitHub")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=False)
    subprocess.run(
        ["git", "commit", "-m", "feat: rebrand to Spider雷达 and Singapore deploy", "--allow-empty"],
        cwd=ROOT,
        check=False,
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)

    clone_url = "https://github.com/SpreadXAI/spider-radar.git"
    if gh_token:
        clone_url = f"https://{gh_token}@github.com/SpreadXAI/spider-radar.git"

    print("==> Read Singapore RDS credentials from tactile gateway")
    db = fetch_db_env()

    print(f"==> Bootstrap spider-radar on {INSTANCE} ({REGION})")
    remote = build_bootstrap_script(jwt_secret, clone_url, db)
    encoded = base64.b64encode(remote.encode()).decode()
    cmd = f"echo {encoded} | base64 -d | bash"
    status, out = run_remote(REGION, INSTANCE, cmd, wait=15, max_wait=1200)
    print(out[-12000:])
    if status != "Success" or "DEPLOY_OK" not in out:
        print(f"Deploy failed: {status}", file=sys.stderr)
        sys.exit(1)

    _, ip_out = run_remote(
        REGION,
        INSTANCE,
        "curl -s ifconfig.me || hostname -I | awk '{print $1}'",
        wait=5,
        max_wait=60,
    )
    public_ip = ip_out.strip().split()[-1]
    print(f"==> Deploy success: http://{public_ip}/")
    print(f"    Admin: admin@spreadx.ai / SpiderRadar@Admin2026")


if __name__ == "__main__":
    main()
