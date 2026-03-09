# JobSpy Platform Design

## Goal
把当前基于 `JobSpy` 的本地脚本升级为一个可容器化、可定时执行、具备前后端界面的职位抓取系统。系统每天晚上 7 点抓取香港 LinkedIn AI 相关岗位，保存全量数据与筛选数据到本地 SQLite，并通过 LLM 过滤出与 `ai`、`llm`、`rag`、`agent` 相关且不是 `junior` / `entry level` 的岗位。

## Scope
- 新建 `backend`，提供 API、抓取编排、LLM 过滤、SQLite 持久化与手动同步入口。
- 新建 `frontend`，默认展示筛选通过的岗位，同时支持切换查看全部岗位。
- 新建 `scheduler` 运行入口，通过容器在每天 19:00 触发同步任务。
- 提供 `docker-compose.yml`、前后端 Dockerfile、本地 Conda 开发说明。

## Non-Goals
- 不接入 Postgres、Redis、消息队列等更重基础设施。
- 第一版不做用户登录、权限控制、多用户配置。
- 第一版不扩展到多招聘网站，先聚焦 LinkedIn 与香港岗位。

## Architecture
系统由三个轻量服务组成：

1. `backend`
   负责职位抓取、LLM 过滤、数据库读写和 REST API 暴露。对外提供职位列表、职位详情、统计信息和手动触发同步接口。

2. `scheduler`
   与 `backend` 共用同一套 Python 代码，通过独立入口执行定时任务。调度器只在每天 19:00 运行一次，并带有保守的抓取节流、受控重试和失败落库记录，避免因高频抓取被 LinkedIn 封禁。

3. `frontend`
   使用 `React + Vite` 实现单页界面，通过后端 API 展示职位数据和同步状态。

所有服务通过 `docker compose` 启动；`backend` 与 `scheduler` 共用同一个 SQLite 数据文件挂载目录。

## Data Model
### `raw_jobs`
保存所有原始抓取结果。

- 去重规则：按 `job_url + date_posted` 作为唯一业务键。
- 若同一职位不同发布时间，则保留为不同记录。
- 保存字段包括标题、公司、地点、发布日期、描述、搜索词、来源站点、本次同步批次等。

### `job_evaluations`
保存 LLM 对职位的判定结果。

- `is_ai_related`
- `is_seniority_allowed`
- `passed`
- `reason`
- `model_name`
- `evaluated_at`
- 关联原始职位记录

### `filtered_jobs`
保存通过筛选的职位快照，用于前端默认列表。

- 与 `raw_jobs` 一对一关联
- 保存筛选通过时的关键展示字段
- 同样按 `job_url + date_posted` 维度保留

### `sync_runs`
记录每次同步任务状态。

- `status`: running / success / partial_success / failed
- `started_at`
- `finished_at`
- `attempt_count`
- `jobs_fetched`
- `jobs_inserted`
- `jobs_evaluated`
- `jobs_filtered`
- `error_message`

## Scraping Flow
1. 创建一条 `sync_runs` 记录。
2. 按关键字顺序执行 LinkedIn 搜索，不并发打 LinkedIn。
3. 每页请求后随机 sleep，保守分页，出现 429 或连接异常时进行有限重试。
4. 如果单个关键字连续失败，记录错误并继续下一个关键字；如果整轮都失败，则把本次同步标记为 `failed`。
5. 合并去重后写入 `raw_jobs`。
6. 对本次新增且未评估的职位执行 LLM 过滤。
7. 通过过滤的职位写入 `filtered_jobs`。
8. 更新 `sync_runs` 汇总信息。

## Retry And Error Handling
- 抓取失败时进行指数退避重试，重试次数受配置控制。
- 对 `429`、超时、代理错误、网络错误分别记录标准化错误类型。
- 单条职位写库失败不应让整个同步任务崩溃；记录后继续。
- LLM 调用失败时重试有限次数，最终失败则把该职位标记为 `evaluation_failed`，以便下轮再次处理。
- 所有严重错误同时写日志与数据库。

## LLM Filtering Contract
输入包含：
- `title`
- `company`
- `location`
- `description`
- `search_term`
- `job_url`

输出必须是结构化 JSON，字段至少包括：
- `is_ai_related`
- `is_seniority_allowed`
- `passed`
- `reason`

判定规则：
- 只保留与 `ai` / `llm` / `rag` / `agent` 明确相关的职位。
- 明确排除 `junior`、`entry level` 及等价初级岗位。

## API Design
- `GET /api/jobs?view=filtered|all&page=1&page_size=20&query=...`
- `GET /api/jobs/{job_id}`
- `GET /api/stats`
- `GET /api/sync-runs`
- `POST /api/jobs/sync`

## Frontend Design
- 顶部统计区域：原始职位数、通过职位数、最近同步时间、最近一次任务状态。
- 主列表默认展示 `filtered` 视图，并可切换到 `all`。
- 每张卡片展示：职位名、公司、地点、发布时间、搜索词、过滤状态、原因、职位链接。
- 提供搜索框和分页控件。
- 若最近同步失败，页面顶部显示警告条并提示查看失败记录。

## Deployment
- `docker-compose.yml` 启动 `frontend`、`backend`、`scheduler`。
- 通过挂载目录持久化 SQLite 数据库和日志。
- 后端与调度器读取 `.env` 中的 LLM 配置。
- 调度使用 cron 风格，默认 `0 19 * * *`。

## Local Development
- 使用 `conda activate linkin`
- 后端依赖通过 `pip install -r backend/requirements.txt`
- 前端依赖通过 `npm install`
- 本地分别启动前后端开发服务，调度器可单次执行命令验证。

## Testing Strategy
- 后端：优先对数据库逻辑、去重逻辑、LLM 过滤解析、同步任务状态机写测试。
- 前端：为列表切换、状态展示和分页查询写基础测试。
- 容器层：至少验证 `docker compose config` 与本地后端测试通过。
