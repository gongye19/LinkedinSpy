# LinkedinSpy

面向 AI/LLM/RAG/Agent 方向岗位的自动化职位平台（LinkedIn）。

- 后端：FastAPI + SQLAlchemy
- 前端：React + Vite
- 调度：APScheduler（默认每天 19:00 HKT）
- 存储：本地可用 SQLite，云端推荐 PostgreSQL（Railway）

## 一键启动（本地）

1. 在项目根目录创建 `.env`：

```env
LLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
LLM_API_KEY=your_key
MODEL_NAME=glm-4.7
```

2. 一条命令启动：

```bash
docker compose up -d --build
```

3. 访问：
- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

停止：

```bash
docker compose down
```

## 一键上云（Railway，最少配置）

本项目已适配 Railway 多服务部署（backend / scheduler / frontend）。

### 1) 新建 4 个服务

- `PostgreSQL`
- `jobspy-backend`（Web）
- `jobspy-scheduler`（Worker）
- `jobspy-frontend`（Web）

仓库都选：`gongye19/LinkedinSpy`

### 2) Root Directory 与启动方式

- backend
  - Root Directory: `/backend`
  - Builder: Dockerfile（自动）
  - Custom Start Command: 留空
- scheduler
  - Root Directory: `/backend`
  - Builder: Dockerfile（自动）
  - Custom Start Command: `python -m app.scheduler`
- frontend
  - Root Directory: `/frontend`
  - Builder: Dockerfile（自动）
  - Custom Start Command: 留空

### 3) 环境变量

backend + scheduler：

```env
DATABASE_URL=postgresql://postgres:***@postgres.railway.internal:5432/railway
LLM_BASE_URL=...
LLM_API_KEY=...
MODEL_NAME=glm-4.7
SCHEDULE_CRON=0 19 * * *
```

仅 backend：

```env
CORS_ORIGINS=https://<your-frontend-domain>
```

仅 frontend：

```env
VITE_API_BASE_URL=https://<your-backend-domain>/api
```

### 4) Networking 端口

以运行日志为准（`Uvicorn running on ...:8080`）。

- backend Target port：`8080`
- frontend Target port：`8080`

### 5) 部署后验证

- `GET https://<backend>/health` 返回 `{"status":"ok"}`
- `GET https://<backend>/api/stats` 返回统计 JSON
- 打开前端域名能看到职位列表页面
- 点击“立即开始爬取”可看到进度

## 核心功能

- 关键词抓取（最多 4 个，前端可编辑）
- LLM 过滤 + 本地规则降级（超时/失败自动 fallback）
- 去重规则：`site + job_url + date_posted`
- dismiss 规则：同岗位同发布日期不再推荐；新发布日期会再次出现
- 同步任务状态追踪（阶段、关键词、进度、失败原因）

## 常用 API

- `GET /api/jobs?view=filtered|all|dismissed`
- `POST /api/jobs/{job_id}/dismiss`
- `GET /api/stats`
- `POST /api/jobs/sync`
- `GET /api/sync-runs`
- `GET /api/sync-runs/{sync_run_id}`
- `GET /api/settings/keywords`
- `PUT /api/settings/keywords`

