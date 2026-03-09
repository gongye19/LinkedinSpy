# JobSpy Platform

## What It Does
- 每天晚上 19:00 自动抓取香港 LinkedIn 岗位（关键词含 `ai engineer`、`llm`、`rag`、`ai agent`）。
- 全量职位写入本地 SQLite。
- 对职位执行 LLM 过滤，保留和 AI/LLM/RAG/Agent 相关且不是 junior/entry-level 的岗位。
- 前端默认展示筛选通过岗位，可切换查看全部岗位。

## Data Storage
SQLite 文件默认路径：
- 本地开发：`data/jobs.db`
- Docker：`./data/jobs.db`（通过 volume 持久化）

去重规则：
- 按 `site + job_url + date_posted` 去重。
- 同一职位不同 `date_posted` 会保留为多条记录。

## Error Handling
- 抓取阶段有受控重试（默认最多 3 次），并带退避等待。
- 重试耗尽后会记录失败状态和错误信息到 `sync_runs`。
- 可以通过 `GET /api/sync-runs` 查看最近任务状态。

## Local Development (Conda)
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

手动触发一次同步：
```bash
conda run -n linkin python -m app.cli
```

## Docker Compose
确保根目录存在 `.env`（可参考 `backend/.env.example`）后启动：

```bash
docker compose up --build -d
```

服务地址：
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

停止：
```bash
docker compose down
```
