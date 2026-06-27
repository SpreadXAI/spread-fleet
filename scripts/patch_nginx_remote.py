#!/usr/bin/env python3
import base64
import json
import os
import sys
import time
from pathlib import Path

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import DescribeInvocationResultsRequest, RunCommandRequest

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "scripts/ecs-deploy.py").read_text()
start = text.index('NGINX_PATCH_SCRIPT = """') + len('NGINX_PATCH_SCRIPT = """')
end = text.index('"""', start)
nginx_script = text[start:end]
nginx_b64 = base64.b64encode(nginx_script.encode()).decode()

cmd = (
    f"echo {nginx_b64} | base64 -d > /tmp/patch_spider-radar_nginx.py && "
    "python3 /tmp/patch_spider-radar_nginx.py && nginx -t && systemctl reload nginx && "
    "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1/ && echo && "
    "curl -sf http://127.0.0.1/api/health"
)

client = AcsClient(os.environ["ALIYUN_ACCESS_KEY_ID"], os.environ["ALIYUN_ACCESS_KEY_SECRET"], "cn-hangzhou")
req = RunCommandRequest.RunCommandRequest()
req.set_InstanceIds([os.environ.get("DEPLOY_INSTANCE", "i-bp18kchcnvcke6ltimn2")])
req.set_CommandContent(cmd)
req.set_Type("RunShellScript")
req.set_accept_format("json")
resp = json.loads(client.do_action_with_exception(req))
invoke_id = resp["InvokeId"]
for _ in range(15):
    time.sleep(4)
    req2 = DescribeInvocationResultsRequest.DescribeInvocationResultsRequest()
    req2.set_InvokeId(invoke_id)
    req2.set_accept_format("json")
    r2 = json.loads(client.do_action_with_exception(req2))
    items = r2.get("Invocation", {}).get("InvocationResults", {}).get("InvocationResult", [])
    if items and items[0].get("InvocationStatus") in ("Success", "Failed"):
        out = items[0].get("Output", "")
        try:
            out = base64.b64decode(out).decode()
        except Exception:
            pass
        print(items[0].get("InvocationStatus"))
        print(out)
        sys.exit(0 if items[0].get("InvocationStatus") == "Success" else 1)
print("timeout")
sys.exit(1)
