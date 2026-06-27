# Cloud.md — Spider雷达 云端测试账号

> 供 Cloud Agent、手工验收与管理台调试使用。测试环境凭证可入库；生产环境勿照抄。

## 环境

| 项 | 值 |
|----|-----|
| **站点** | http://43.98.185.179/ |
| **API** | http://43.98.185.179/api/ |
| **区域** | 新加坡 `ap-southeast-1` |
| **ECS** | `i-t4n571mpi11mkib9ubxj`（2 核 4G） |
| **数据库** | 新加坡 RDS / schema `spider_radar` |

## 普通测试账号（推荐日常使用）

| 项 | 值 |
|----|-----|
| **邮箱** | `qa-test@spreadx.ai` |
| **密码** | `SpiderRadar@Test2026` |
| **显示名** | QA 测试 |
| **角色** | 普通用户（非管理员） |
| **默认空间** | QA 测试空间 |

### API 登录

```bash
curl -s -X POST "http://43.98.185.179/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"qa-test@spreadx.ai","password":"SpiderRadar@Test2026"}'
```

## 管理员账号

| 项 | 值 |
|----|-----|
| **邮箱** | `admin@spreadx.ai` |
| **密码** | `SpiderRadar@Admin2026` |
| **角色** | `is_admin=true` |
| **管理台** | http://43.98.185.179/admin（需先主站登录，个人资料页新标签打开） |

### API 登录

```bash
curl -s -X POST "http://43.98.185.179/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@spreadx.ai","password":"SpiderRadar@Admin2026"}'
```

## 种子脚本（部署时自动创建/重置密码）

```bash
cd /opt/spider-radar/backend
export PYTHONPATH=.
python scripts/seed_data.py 200
```

账号定义见 `backend/app/config.py`：`admin_email` / `qa_email` 及对应密码。

## E2E

```bash
cd frontend
E2E_BASE_URL=http://43.98.185.179 npm run test:e2e
```

## Tactile 生产对接

| 项 | 值 |
|----|-----|
| **Tactile API** | `https://foxrouter.com/api` |
| **工作空间** | SpreadX-twitter（workspace_id=6） |
| **执行 Agent** | Spider Radar Twitter Executor（agent_id=5） |
| **Bridge 用户** | `spider-radar-bridge@spreadx.ai`（API Key 存服务器 `.env`，勿入库） |

### 用户流程

1. 登录 Spider雷达 → 购号 → 进入账号详情
2. 填写 Twitter Session Cookie → **保存 Cookie**
3. 配置 Prompt → **立即执行** → 后端 `POST /api/my/accounts/{id}/run` 派发到 Tactile
4. Cookie 等运行时变量通过 Tactile `dispatch_env_json` 注入 worker（不再写入 prompt content）
5. 在 [foxrouter.com](https://foxrouter.com) SpreadX-twitter 空间查看 work 状态

### 服务器环境变量（`backend/.env`）

```
TACTILE_API_BASE=https://foxrouter.com/api
TACTILE_API_KEY=<bridge user api key>
TACTILE_WORKSPACE_ID=6
TACTILE_AGENT_ID=5
```

### Agent 回调（可选）

Tactile Agent 可通过 `POST /api/tactile/callback/logs` 回写执行日志，请求头：

`X-Tactile-Callback-Secret: <TACTILE_API_KEY 或 TACTILE_CALLBACK_SECRET>`
