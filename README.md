# Spider雷达（Spread-Sonar）

社媒账号舰队管理与任务编排平台。

| 项 | 值 |
|----|-----|
| GitHub | https://github.com/SpreadXAI/spider-radar |
| 生产（新加坡） | http://43.98.185.179/ |
| ECS | `i-t4n571mpi11mkib9ubxj`（2 核 4G，ap-southeast-1a） |
| 数据库 | 新加坡 RDS `tactile` / schema `spider_radar` |

## 本地开发

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=.
uvicorn app.main:app --reload --port 9092

cd frontend && npm install && npm run dev
```

## 部署（新加坡）

```bash
python3 scripts/deploy-singapore.py
```

**禁止**使用已废弃的 `scripts/ecs-deploy.py`（杭州）。

## 管理员

见 [Cloud.md](./Cloud.md)（含普通测试账号 `qa-test@spreadx.ai`）。

## E2E

```bash
cd frontend && npm ci && npx playwright install chromium
E2E_BASE_URL=http://43.98.185.179 npm run test:e2e
```
