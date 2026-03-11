from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class JobItem(BaseModel):
    id: int
    site: str
    job_url: str
    title: str
    company: str | None = None
    location: str | None = None
    search_term: str | None = None
    date_posted: date | None = None
    filter_reason: str | None = None
    dismiss_reason: str | None = None


class JobsResponse(BaseModel):
    view: str
    items: list[JobItem]


class StatsResponse(BaseModel):
    raw_jobs: int
    filtered_jobs: int
    dismissed_jobs: int
    latest_sync_status: str | None = None
    latest_sync_finished_at: str | None = None


class SyncRunItem(BaseModel):
    id: int
    status: str
    attempt_count: int
    jobs_fetched: int
    jobs_inserted: int
    jobs_evaluated: int
    jobs_filtered: int
    total_keywords: int
    completed_keywords: int
    current_stage: str | None = None
    current_keyword: str | None = None
    progress_message: str | None = None
    error_message: str | None = None
    started_at: str
    finished_at: str | None = None


class TriggerSyncResponse(BaseModel):
    sync_run_id: int


class KeywordSettingsResponse(BaseModel):
    keywords: list[str]
    llm_rules: list[str]


class KeywordSettingsUpdateRequest(BaseModel):
    keywords: list[str]
    llm_rules: list[str] = []
