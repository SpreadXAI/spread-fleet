#!/usr/bin/env python3
"""DEPRECATED: Hangzhou deploy disabled. Use scripts/deploy-singapore.py for Spread-Sonar."""

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
INSTANCE = os.environ.get("DEPLOY_INSTANCE", "i-bp18kchcnvcke6ltimn2")
REGION = "cn-hangzhou"
API_PORT = 9092

NGINX_PATCH_SCRIPT = """from pathlib import Path

spider-radar = '''    # spider-radar-managed
    location = / {
        return 302 /;
    }
    location / {
        root /var/www;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:9092/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }
    location = /agent-ops {
        return 302 /;
    }
    location /agent-ops/ {
        return 302 /;
    }
    location /agent-ops/api/ {
        proxy_pass http://127.0.0.1:9092/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }
    # spider-radar-managed-end
'''

for path_name, anchor in [
    ("/etc/nginx/sites-enabled/api.imjson.cn", "    # tactile-app-managed"),
    ("/etc/nginx/sites-enabled/data-air-tran", "    location = / {"),
]:
    path = Path(path_name)
    text = path.read_text()
    if "# spider-radar-managed" in text:
        print(f"skip {path_name}")
        continue
    if "# agent-ops-managed" in text:
        start = text.index("    # agent-ops-managed")
        end = text.index("    # agent-ops-managed-end") + len("    # agent-ops-managed-end\\n")
        text = text[:start] + spider-radar + text[end:]
        path.write_text(text)
        print(f"replaced agent-ops block in {path_name}")
        continue
    if anchor not in text:
        raise SystemExit(f"anchor not found in {path_name}")
    path.write_text(text.replace(anchor, spider-radar + anchor, 1))
    print(f"patched {path_name}")
"""


def run_remote(cmd: str, wait: int = 8, max_wait: int = 420) -> tuple[str, str]:
    client = AcsClient(os.environ["ALIYUN_ACCESS_KEY_ID"], os.environ["ALIYUN_ACCESS_KEY_SECRET"], REGION)
    req = RunCommandRequest.RunCommandRequest()
    req.set_InstanceIds([INSTANCE])
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


def build_remote_script(jwt_secret: str, clone_url: str) -> str:
    jwt_secret_esc = jwt_secret.replace("'", "'\"'\"'")
    nginx_b64 = base64.b64encode(NGINX_PATCH_SCRIPT.encode()).decode()
    return f"""#!/bin/bash
set -euo pipefail
export JWT_SECRET='{jwt_secret_esc}'
REMOTE_DIR=/opt/spider-radar
WEB_DIR=/var/www/
API_PORT={API_PORT}
CLONE_URL='{clone_url}'
SERVICE=spider-radar-api

GW_PID=$(pgrep -f "uvicorn gateway.app.main:app" | head -1)
export DATABASE_PASSWORD=$(tr '\\0' '\\n' < /proc/$GW_PID/environ | sed -n 's/^DF_DATABASE_PASSWORD=//p')
export DATABASE_HOST=$(tr '\\0' '\\n' < /proc/$GW_PID/environ | sed -n 's/^DF_DATABASE_HOST=//p')
export DATABASE_USER=$(tr '\\0' '\\n' < /proc/$GW_PID/environ | sed -n 's/^DF_DATABASE_USER=//p')
export DATABASE_NAME=$(tr '\\0' '\\n' < /proc/$GW_PID/environ | sed -n 's/^TACTILE_DATABASE_NAME=//p')
if [ -z "$DATABASE_PASSWORD" ]; then echo "missing DB password from tactile"; exit 1; fi

mkdir -p "$REMOTE_DIR" "$WEB_DIR"
if [ -d "$REMOTE_DIR/.git" ]; then
  cd "$REMOTE_DIR" && git remote set-url origin "$CLONE_URL" && git fetch origin main && git reset --hard origin/main
elif [ -d /opt/agent-ops/.git ]; then
  mv /opt/agent-ops "$REMOTE_DIR"
  cd "$REMOTE_DIR" && git remote set-url origin "$CLONE_URL" && git fetch origin main && git reset --hard origin/main
else
  rm -rf "$REMOTE_DIR"/* "$REMOTE_DIR"/.[!.]* 2>/dev/null || true
  git clone "$CLONE_URL" "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"

python3 -m venv .venv
. .venv/bin/activate
pip install -q -r backend/requirements.txt

cat > backend/.env << EOF
ENVIRONMENT=test
DATABASE_PASSWORD=$DATABASE_PASSWORD
DATABASE_HOST=$DATABASE_HOST
DATABASE_USER=$DATABASE_USER
DATABASE_NAME=$DATABASE_NAME
JWT_SECRET=$JWT_SECRET
EOF

export PYTHONPATH=backend
cd backend
python -c "from app.database import ensure_schema; from app.models import Base; from app.database import engine; ensure_schema(); Base.metadata.create_all(bind=engine)"
python scripts/migrate_schema.py
python scripts/seed_data.py 200

cd "$REMOTE_DIR"
deactivate || true

systemctl stop agent-ops-api 2>/dev/null || true
systemctl disable agent-ops-api 2>/dev/null || true

cat > /etc/systemd/system/$SERVICE.service << UNIT
[Unit]
Description=Spider雷达 API (test)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/spider-radar/backend
EnvironmentFile=/opt/spider-radar/backend/.env
Environment=PYTHONPATH=/opt/spider-radar/backend
ExecStart=/opt/spider-radar/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $API_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable $SERVICE
systemctl restart $SERVICE
sleep 3
curl -sf http://127.0.0.1:$API_PORT/health || (journalctl -u $SERVICE -n 40 --no-pager; exit 1)

cd "$REMOTE_DIR/frontend"
if [ ! -d node_modules ]; then npm ci || npm install; fi
npm run build
rm -rf "$WEB_DIR"/*
cp -r dist/* "$WEB_DIR/"
chown -R root:root "$WEB_DIR"

echo {nginx_b64} | base64 -d > /tmp/patch_spider-radar_nginx.py
python3 /tmp/patch_spider-radar_nginx.py
nginx -t && systemctl reload nginx

echo DEPLOY_OK
curl -sf -o /dev/null -w "%{{http_code}}" http://127.0.0.1/
"""


def main() -> None:
    print(
        "ERROR: Hangzhou (118.31.57.25) deploy is disabled.\n"
        "Spread-Sonar must deploy to Singapore (foxrouter.com / ap-southeast-1).\n"
        "Hangzhou spider-radar has been torn down. Singapore deploy script: TBD.",
        file=sys.stderr,
    )
    sys.exit(1)

    jwt_secret = os.environ.get("JWT_SECRET", "spider-radar-test-jwt-secret-4918")
    gh_token = os.environ.get("github_access_token") or os.environ.get("GH_TOKEN", "")

    print("==> Push latest to GitHub")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=False)
    subprocess.run(
        ["git", "commit", "-m", "chore: deploy release", "--allow-empty"],
        cwd=ROOT,
        check=False,
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)

    clone_url = "https://github.com/SpreadXAI/spider-radar.git"
    if gh_token:
        clone_url = f"https://{gh_token}@github.com/SpreadXAI/spider-radar.git"

    remote_script = build_remote_script(jwt_secret, clone_url)
    encoded = base64.b64encode(remote_script.encode()).decode()
    cmd = f"echo {encoded} | base64 -d | bash"
    status, out = run_remote(cmd, wait=15, max_wait=600)
    print(out)
    if status != "Success" or "DEPLOY_OK" not in out:
        print(f"Deploy failed: {status}", file=sys.stderr)
        sys.exit(1)
    print("==> Deploy success: http://118.31.57.25/")


if __name__ == "__main__":
    main()
