# Spread-Sonar（传播声纳）

社媒账号舰队管理与任务编排平台。

> 产品名：**Spread-Sonar**。仓库仍为 `spread-fleet`（GitHub: SpreadXAI/spread-fleet）。

- Frontend: Vue 3 + Vite + Tailwind
- Backend: FastAPI + PostgreSQL
- **部署区域：新加坡（ap-southeast-1）**，与 Tactile 生产（foxrouter.com）同区域

## 部署说明

**禁止部署到杭州（118.31.57.25）。** 原杭州测试实例已下线。

新加坡部署脚本（待建）：

```bash
python3 scripts/deploy-singapore.py
```

## 本地开发

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=.
uvicorn app.main:app --reload --port 9092

cd frontend && npm install && npm run dev
```

## E2E

本地或新加坡环境 URL 由 `E2E_BASE_URL` 指定。

```bash
cd frontend && npm ci && npx playwright install chromium
E2E_BASE_URL=https://<singapore-host>/spread-sonar npm run test:e2e
```
