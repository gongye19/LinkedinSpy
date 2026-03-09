from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import random
import time
from typing import Any

from app.db import SessionFactory
from app.models import SyncRun


class SyncService:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        max_attempts: int = 3,
        base_delay_seconds: float = 2.0,
        jitter_seconds: float = 1.0,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.jitter_seconds = jitter_seconds
        self.sleep_func = sleep_func or time.sleep

    def create_run(self) -> int:
        with self.session_factory() as session:
            sync_run = SyncRun(
                status="running",
                attempt_count=0,
                current_stage="queued",
                progress_message="Task queued",
            )
            session.add(sync_run)
            session.commit()
            session.refresh(sync_run)
            return sync_run.id

    def run(self, *, job_fetcher: Callable[[int, Callable[..., None]], Any]) -> int:
        sync_run_id = self.create_run()
        self.execute_run(sync_run_id=sync_run_id, job_fetcher=job_fetcher)
        return sync_run_id

    def execute_run(
        self,
        *,
        sync_run_id: int,
        job_fetcher: Callable[[int, Callable[..., None]], Any],
    ) -> None:
        self.update_progress(sync_run_id, stage="running", message="Sync started")

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = job_fetcher(sync_run_id, self.update_progress) or {}
                with self.session_factory() as session:
                    sync_run = session.get(SyncRun, sync_run_id)
                    sync_run.status = "success"
                    sync_run.attempt_count = attempt
                    sync_run.jobs_fetched = int(result.get("jobs_fetched", 0))
                    sync_run.jobs_inserted = int(result.get("jobs_inserted", 0))
                    sync_run.jobs_evaluated = int(result.get("jobs_evaluated", 0))
                    sync_run.jobs_filtered = int(result.get("jobs_filtered", 0))
                    sync_run.total_keywords = int(result.get("total_keywords", sync_run.total_keywords))
                    sync_run.completed_keywords = int(result.get("completed_keywords", sync_run.completed_keywords))
                    sync_run.current_stage = "completed"
                    sync_run.progress_message = "Sync completed"
                    sync_run.finished_at = datetime.now(UTC)
                    session.commit()
                return
            except Exception as exc:
                with self.session_factory() as session:
                    sync_run = session.get(SyncRun, sync_run_id)
                    sync_run.attempt_count = attempt
                    sync_run.error_message = str(exc)
                    sync_run.current_stage = "error"
                    sync_run.progress_message = f"Attempt {attempt} failed: {exc}"
                    if attempt >= self.max_attempts:
                        sync_run.status = "failed"
                        sync_run.finished_at = datetime.now(UTC)
                    session.commit()

                if attempt >= self.max_attempts:
                    return

                self.sleep_func(self._compute_delay(attempt))

    def update_progress(
        self,
        sync_run_id: int,
        *,
        stage: str | None = None,
        keyword: str | None = None,
        total_keywords: int | None = None,
        completed_keywords: int | None = None,
        message: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            sync_run = session.get(SyncRun, sync_run_id)
            if sync_run is None:
                return
            if stage is not None:
                sync_run.current_stage = stage
            if keyword is not None:
                sync_run.current_keyword = keyword
            if total_keywords is not None:
                sync_run.total_keywords = total_keywords
            if completed_keywords is not None:
                sync_run.completed_keywords = completed_keywords
            if message is not None:
                sync_run.progress_message = message
            session.commit()

    def _compute_delay(self, attempt: int) -> float:
        return self.base_delay_seconds * attempt + random.uniform(0, self.jitter_seconds)
