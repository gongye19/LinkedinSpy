# JobSpy Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a containerized job scraping platform with a FastAPI backend, React frontend, daily scheduler, SQLite persistence, LLM-based job filtering, and robust retry/error recording.

**Architecture:** A Python backend owns scraping, persistence, filtering, and API responses. A separate scheduler entrypoint reuses backend services to run the daily 19:00 sync with conservative rate limiting and retry logic. A React frontend consumes backend APIs and presents filtered or all jobs from SQLite-backed storage.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, APScheduler or cron-compatible scheduler loop, SQLite, requests/pandas/JobSpy, React, Vite, TypeScript, Docker Compose.

---

### Task 1: Scaffold Backend Project

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Test: `backend/tests/test_config.py`

**Step 1: Write the failing test**

```python
from app.config import Settings


def test_settings_default_schedule():
    settings = Settings()
    assert settings.schedule_cron == "0 19 * * *"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: FAIL because backend app package does not exist yet.

**Step 3: Write minimal implementation**

Create backend package, base settings, and a minimal FastAPI app that can boot.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: scaffold backend service"
```

### Task 2: Add Database Models And Deduplication Rules

**Files:**
- Modify: `backend/app/db.py`
- Modify: `backend/app/models.py`
- Create: `backend/app/repositories.py`
- Test: `backend/tests/test_deduplication.py`

**Step 1: Write the failing test**

```python
def test_same_job_url_with_different_date_posted_is_kept(session):
    # insert two raw job records with same url but different date_posted
    # assert both remain
    ...
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_deduplication.py -v`
Expected: FAIL because tables/repositories are missing.

**Step 3: Write minimal implementation**

Add `raw_jobs`, `job_evaluations`, `filtered_jobs`, and `sync_runs` tables with uniqueness rules based on `job_url + date_posted`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_deduplication.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add sqlite persistence models"
```

### Task 3: Extract Scraping Service From Existing Logic

**Files:**
- Create: `backend/app/services/scraper.py`
- Create: `backend/app/services/jobspy_loader.py`
- Test: `backend/tests/test_scraper_service.py`

**Step 1: Write the failing test**

```python
def test_scraper_merges_keywords_and_deduplicates_on_url_and_date():
    ...
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_scraper_service.py -v`
Expected: FAIL because scraper service does not exist.

**Step 3: Write minimal implementation**

Port the current `run.py` logic into a reusable backend service, keeping keyword-based scraping, merge, and deduplication while enabling richer fields for filtering.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_scraper_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add job scraping service"
```

### Task 4: Add Retry, Backoff, And Failure Recording

**Files:**
- Create: `backend/app/services/sync.py`
- Create: `backend/app/services/errors.py`
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_sync_retries.py`

**Step 1: Write the failing test**

```python
def test_sync_records_failure_after_retries_exhausted():
    ...
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_sync_retries.py -v`
Expected: FAIL because retry orchestration and sync run tracking are missing.

**Step 3: Write minimal implementation**

Implement sync orchestration with conservative retries, random delays, and standardized failure recording in `sync_runs`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_sync_retries.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add sync retries and failure tracking"
```

### Task 5: Add LLM Filtering Service

**Files:**
- Create: `backend/app/services/llm.py`
- Create: `backend/app/services/filtering.py`
- Test: `backend/tests/test_filtering_service.py`

**Step 1: Write the failing test**

```python
def test_filtering_rejects_entry_level_jobs():
    ...
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_filtering_service.py -v`
Expected: FAIL because LLM filtering service does not exist.

**Step 3: Write minimal implementation**

Implement structured LLM evaluation using environment variables, parse JSON response, persist evaluations, and promote passing jobs into `filtered_jobs`.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_filtering_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add llm-based job filtering"
```

### Task 6: Expose Backend APIs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_api_jobs.py`

**Step 1: Write the failing test**

```python
def test_jobs_endpoint_defaults_to_filtered_view(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_api_jobs.py -v`
Expected: FAIL because routes are missing.

**Step 3: Write minimal implementation**

Expose endpoints for jobs, job detail, stats, sync history, and manual sync trigger.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_api_jobs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add job listing api"
```

### Task 7: Scaffold Frontend App

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Test: `frontend/src/App.test.tsx`

**Step 1: Write the failing test**

```tsx
it("shows filtered jobs tab by default", () => {
  render(<App />);
  expect(screen.getByText("通过岗位")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- App.test.tsx`
Expected: FAIL because frontend app does not exist.

**Step 3: Write minimal implementation**

Scaffold the Vite React app with a clean dashboard layout and default filtered view toggle.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- App.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold frontend app"
```

### Task 8: Build Frontend Data Views

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/components/StatsBar.tsx`
- Create: `frontend/src/components/JobList.tsx`
- Create: `frontend/src/components/JobCard.tsx`
- Test: `frontend/src/App.test.tsx`

**Step 1: Write the failing test**

```tsx
it("toggles between filtered and all jobs views", async () => {
  ...
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- App.test.tsx`
Expected: FAIL because data view behavior is missing.

**Step 3: Write minimal implementation**

Connect the frontend to backend APIs and render stats, toggles, cards, pagination, and error banners.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- App.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: build jobs dashboard"
```

### Task 9: Add Scheduler Entrypoint And Compose Setup

**Files:**
- Create: `backend/app/scheduler.py`
- Create: `backend/app/cli.py`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Test: `backend/tests/test_scheduler_config.py`

**Step 1: Write the failing test**

```python
def test_scheduler_uses_daily_7pm_cron():
    ...
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_scheduler_config.py -v`
Expected: FAIL because scheduler config does not exist.

**Step 3: Write minimal implementation**

Add scheduler entrypoint, backend/frontend Dockerfiles, compose wiring, environment handling, and SQLite/log volume mounts.

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_scheduler_config.py -v && docker compose config`
Expected: PASS and valid compose configuration.

**Step 5: Commit**

```bash
git add backend frontend docker-compose.yml
git commit -m "feat: add scheduled container deployment"
```

### Task 10: Add Local Development And Operations Docs

**Files:**
- Create: `backend/.env.example`
- Create: `README_PLATFORM.md`
- Modify: `README.md`

**Step 1: Write the failing test**

No code test required; validate docs completeness against the design.

**Step 2: Run test to verify it fails**

Review against checklist:
- Conda environment documented
- Backend install documented
- Frontend install documented
- Docker compose startup documented
- Manual sync documented

Expected: Incomplete before docs are written.

**Step 3: Write minimal implementation**

Document `conda activate linkin`, dependency installation, local startup, daily scheduler behavior, retry/failure logging, and Docker Compose usage.

**Step 4: Run test to verify it passes**

Run:
- `python -m compileall backend/app`
- `docker compose config`
- manual checklist review

Expected: Commands succeed and docs cover all operational requirements.

**Step 5: Commit**

```bash
git add README.md README_PLATFORM.md backend/.env.example
git commit -m "docs: add platform usage guide"
```
