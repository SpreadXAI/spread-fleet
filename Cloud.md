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
