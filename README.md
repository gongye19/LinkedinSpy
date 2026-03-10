# LinkedinSpy

一个面向香港 AI 岗位的自动化职位发现系统。  
项目包含后端、前端和定时调度，支持：

- 按关键词批量抓取 LinkedIn 职位
- 使用大模型进行岗位相关性过滤（支持失败自动降级）
- SQLite 本地持久化（全量 / 过滤 / 忽略 / 任务状态）
- 前端查看职位、dismiss、关键词管理、实时进度
- 手动立即爬取 + 每天 19:00 自动爬取

---

## 当前能力

- 关键词最多 4 个，可在前端配置，默认：
  - `ai engineer`
  - `llm`
  - `rag`
  - `data scientist`
- 每个关键词单独跑一轮抓取（串行）
- 单轮抓取默认参数：
  - `site_name=["linkedin"]`
  - `location="Hong Kong"`
  - `hours_old=24`
  - `results_wanted=50`
  - `linkedin_fetch_description=True`
- 去重规则：`site + job_url + date_posted`
- dismiss 规则：已 dismiss 的同岗位同发布日期不会再推荐；若该岗位新发布日期出现，会重新推荐

---

## 项目结构

```text
JobSpy/
├── backend/                 # FastAPI + SQLite + 抓取编排 + LLM过滤
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React + Vite 看板
│   ├── src/
│   └── Dockerfile
├── docker-compose.yml
├── data/                    # SQLite 数据文件目录（运行后生成）
└── .env                     # LLM 配置（本地）
```

---

## 环境变量

在项目根目录放置 `.env`：

```env
LLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
LLM_API_KEY=your_key
MODEL_NAME=glm-4.7
```

可选：

```env
DATABASE_URL=sqlite:////app/data/jobs.db
SCHEDULE_CRON=0 19 * * *
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

---

## 启动方式（推荐 Docker）

```bash
cd /Users/han/Desktop/code/ideas/JobSpy
docker compose up --build -d
```

访问：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

停止：

```bash
docker compose down
```

---

## 本地开发（Conda）

```bash
conda activate linkin
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

启动后端：

```bash
conda run -n linkin uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

启动前端：

```bash
cd frontend
npm run dev
```

---

## 前端功能

- 查看通过岗位 / 全部岗位 / 已忽略岗位
- dismiss 岗位
- 编辑并保存关键词（最多 4 个）
- 立即开始爬取
- 实时进度显示：
  - 当前阶段（爬取关键词中 / 大模型处理中 / 已结束）
  - 当前关键词
  - 关键词进度
  - 进度条
  - 本轮更新结果（抓取条数、新增条数、列表已刷新）

---

## 后端 API

- `GET /api/jobs?view=filtered|all|dismissed`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/dismiss`
- `GET /api/stats`
- `GET /api/sync-runs`
- `GET /api/sync-runs/{sync_run_id}`
- `POST /api/jobs/sync`
- `GET /api/settings/keywords`
- `PUT /api/settings/keywords`

---

## 调度与容错

- 调度器默认每天 `19:00` 自动运行
- 支持手动触发即时同步
- 同步任务有重试和状态记录
- LLM 调用超时/失败时自动回退本地规则，保证任务可继续完成

---

## 数据表说明（SQLite）

- `raw_jobs`：全量抓取结果
- `job_evaluations`：LLM/降级规则判定结果
- `filtered_jobs`：通过筛选的岗位
- `dismissed_jobs`：用户忽略的岗位（按岗位+发布日期）
- `sync_runs`：任务执行状态与进度
- `crawl_keyword_configs`：关键词配置（最多4个）

---

## 常见问题

### 1) 为什么任务会失败？
- 看前端“最近任务状态”或 `GET /api/sync-runs` 的 `error_message`
- 常见为网络波动或外部服务超时

### 2) 为什么某些岗位不会再出现？
- 你可能 dismiss 过该岗位对应发布日期
- 如果该岗位以新发布日期重新发布，会再次出现

### 3) 为什么我看不到更新？
- 检查前端进度卡是否显示“已结束”
- 列表上方会显示“本轮已结束：抓取 X 条，新增 Y 条，已刷新列表”

