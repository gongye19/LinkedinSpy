from __future__ import annotations

from collections.abc import Callable
from datetime import date
import threading
from typing import Any

from sqlalchemy import func, select

from app.config import Settings
from app.db import SessionFactory
from app.models import CrawlKeywordConfig, DismissedJob, FilteredJob, RawJob, SyncRun
from app.repositories import RawJobRepository
from app.services.filtering import JobFilteringService
from app.services.llm import LLMClient
from app.services.scraper import LinkedInScraperService
from app.services.sync import SyncService


DEFAULT_SEARCH_TERMS = ["ai engineer", "llm", "rag", "data scientist"]


def run_sync_pipeline(
    *,
    session_factory: SessionFactory,
    settings: Settings,
    scrape_callable: Callable[..., Any] | None = None,
) -> int:
    sync_service = SyncService(session_factory=session_factory, max_attempts=3)

    def job_fetcher(sync_run_id: int, progress_updater: Callable[..., None]) -> dict[str, int]:
        keywords = get_search_terms(session_factory)
        total_keywords = len(keywords)
        progress_updater(
            sync_run_id,
            stage="scraping",
            total_keywords=total_keywords,
            completed_keywords=0,
            message="Starting keyword scraping",
        )
        scraper = LinkedInScraperService(
            search_terms=keywords,
            location="Hong Kong",
            hours_old=24,
            results_wanted=50,
            verbose=1,
            linkedin_fetch_description=True,
        )
        jobs = scraper.scrape(
            scrape_callable=scrape_callable,
            progress_callback=lambda *, keyword, completed_keywords, total_keywords, message: progress_updater(
                sync_run_id,
                stage="scraping",
                keyword=keyword,
                completed_keywords=completed_keywords,
                total_keywords=total_keywords,
                message=message,
            ),
        )
        jobs_fetched = len(jobs)
        jobs_inserted = 0
        jobs_evaluated = 0
        jobs_filtered = 0

        llm_client = _build_llm_client(settings)

        with session_factory() as session:
            repository = RawJobRepository(session)
            filtering_service = JobFilteringService(session=session, model_name=settings.model_name)
            progress_updater(
                sync_run_id,
                stage="llm_processing",
                keyword=None,
                message=f"Processing {len(jobs)} jobs with LLM",
            )

            for idx, job in enumerate(jobs, start=1):
                raw_job, created = repository.create_or_get_with_flag(
                    {
                        "site": job.get("site", "linkedin"),
                        "job_url": job["job_url"],
                        "title": job.get("title", "Unknown"),
                        "company": job.get("company"),
                        "location": job.get("location"),
                        "description": job.get("description"),
                        "search_term": job.get("search_term"),
                        "date_posted": _parse_date(job.get("date_posted")),
                    }
                )

                if created:
                    jobs_inserted += 1

                evaluation = filtering_service.evaluate_and_store(
                    raw_job,
                    evaluator=(
                        llm_client.evaluate_job
                        if llm_client is not None
                        else _fallback_evaluator
                    ),
                )
                jobs_evaluated += 1
                if evaluation.passed:
                    jobs_filtered += 1
                if idx == 1 or idx % 5 == 0 or idx == len(jobs):
                    progress_updater(
                        sync_run_id,
                        stage="llm_processing",
                        message=f"LLM processed {idx}/{len(jobs)} jobs",
                    )

            session.commit()

        return {
            "jobs_fetched": jobs_fetched,
            "jobs_inserted": jobs_inserted,
            "jobs_evaluated": jobs_evaluated,
            "jobs_filtered": jobs_filtered,
            "total_keywords": total_keywords,
            "completed_keywords": total_keywords,
        }

    return sync_service.run(job_fetcher=job_fetcher)


def start_sync_pipeline_async(
    *,
    session_factory: SessionFactory,
    settings: Settings,
    scrape_callable: Callable[..., Any] | None = None,
) -> int:
    sync_service = SyncService(session_factory=session_factory, max_attempts=3)
    sync_run_id = sync_service.create_run()

    def job_fetcher(sync_run_id: int, progress_updater: Callable[..., None]) -> dict[str, int]:
        return _run_pipeline_job_fetcher(
            sync_run_id=sync_run_id,
            progress_updater=progress_updater,
            session_factory=session_factory,
            settings=settings,
            scrape_callable=scrape_callable,
        )

    thread = threading.Thread(
        target=sync_service.execute_run,
        kwargs={"sync_run_id": sync_run_id, "job_fetcher": job_fetcher},
        daemon=True,
    )
    thread.start()
    return sync_run_id


def _run_pipeline_job_fetcher(
    *,
    sync_run_id: int,
    progress_updater: Callable[..., None],
    session_factory: SessionFactory,
    settings: Settings,
    scrape_callable: Callable[..., Any] | None,
) -> dict[str, int]:
    # Reuse the same logic as run_sync_pipeline for async entrypoint.
    keywords = get_search_terms(session_factory)
    total_keywords = len(keywords)
    progress_updater(
        sync_run_id,
        stage="scraping",
        total_keywords=total_keywords,
        completed_keywords=0,
        message="Starting keyword scraping",
    )
    scraper = LinkedInScraperService(
        search_terms=keywords,
        location="Hong Kong",
        hours_old=24,
        results_wanted=50,
        verbose=1,
        linkedin_fetch_description=True,
    )
    jobs = scraper.scrape(
        scrape_callable=scrape_callable,
        progress_callback=lambda *, keyword, completed_keywords, total_keywords, message: progress_updater(
            sync_run_id,
            stage="scraping",
            keyword=keyword,
            completed_keywords=completed_keywords,
            total_keywords=total_keywords,
            message=message,
        ),
    )
    jobs_fetched = len(jobs)
    jobs_inserted = 0
    jobs_evaluated = 0
    jobs_filtered = 0
    llm_client = _build_llm_client(settings)

    with session_factory() as session:
        repository = RawJobRepository(session)
        filtering_service = JobFilteringService(session=session, model_name=settings.model_name)
        progress_updater(
            sync_run_id,
            stage="llm_processing",
            keyword=None,
            message=f"Processing {len(jobs)} jobs with LLM",
        )
        for idx, job in enumerate(jobs, start=1):
            raw_job, created = repository.create_or_get_with_flag(
                {
                    "site": job.get("site", "linkedin"),
                    "job_url": job["job_url"],
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "description": job.get("description"),
                    "search_term": job.get("search_term"),
                    "date_posted": _parse_date(job.get("date_posted")),
                }
            )
            if created:
                jobs_inserted += 1
            evaluation = filtering_service.evaluate_and_store(
                raw_job,
                evaluator=(llm_client.evaluate_job if llm_client is not None else _fallback_evaluator),
            )
            jobs_evaluated += 1
            if evaluation.passed:
                jobs_filtered += 1
            if idx == 1 or idx % 5 == 0 or idx == len(jobs):
                progress_updater(
                    sync_run_id,
                    stage="llm_processing",
                    message=f"LLM processed {idx}/{len(jobs)} jobs",
                )
        session.commit()

    return {
        "jobs_fetched": jobs_fetched,
        "jobs_inserted": jobs_inserted,
        "jobs_evaluated": jobs_evaluated,
        "jobs_filtered": jobs_filtered,
        "total_keywords": total_keywords,
        "completed_keywords": total_keywords,
    }


def get_search_terms(session_factory: SessionFactory) -> list[str]:
    with session_factory() as session:
        config = session.execute(
            select(CrawlKeywordConfig).order_by(CrawlKeywordConfig.id.desc()).limit(1)
        ).scalar_one_or_none()
        if config is None:
            return DEFAULT_SEARCH_TERMS

        keywords = [
            config.keyword_1.strip() if config.keyword_1 else "",
            config.keyword_2.strip() if config.keyword_2 else "",
            config.keyword_3.strip() if config.keyword_3 else "",
            config.keyword_4.strip() if config.keyword_4 else "",
        ]
        keywords = [item for item in keywords if item]
        return keywords if keywords else DEFAULT_SEARCH_TERMS


def get_stats(session_factory: SessionFactory) -> dict[str, Any]:
    with session_factory() as session:
        raw_jobs = session.execute(select(func.count(RawJob.id))).scalar_one()
        filtered_jobs = session.execute(
            select(func.count(FilteredJob.id))
            .select_from(FilteredJob)
            .outerjoin(DismissedJob, DismissedJob.raw_job_id == FilteredJob.raw_job_id)
            .where(DismissedJob.id.is_(None))
        ).scalar_one()
        dismissed_jobs = session.execute(select(func.count(DismissedJob.id))).scalar_one()

        latest_sync = session.execute(
            select(SyncRun).order_by(SyncRun.id.desc()).limit(1)
        ).scalar_one_or_none()

        return {
            "raw_jobs": int(raw_jobs),
            "filtered_jobs": int(filtered_jobs),
            "dismissed_jobs": int(dismissed_jobs),
            "latest_sync_status": latest_sync.status if latest_sync else None,
            "latest_sync_finished_at": (
                latest_sync.finished_at.isoformat()
                if latest_sync and latest_sync.finished_at
                else None
            ),
        }


def _build_llm_client(settings: Settings) -> LLMClient | None:
    if settings.llm_base_url and settings.llm_api_key:
        return LLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model_name=settings.model_name,
        )
    return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _fallback_evaluator(payload: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(payload.get(key, "") or "")
        for key in ("title", "description", "search_term")
    ).lower()
    ai_related = any(token in text for token in ("ai", "llm", "rag", "agent"))
    seniority_allowed = not any(token in text for token in ("junior", "entry level"))
    passed = ai_related and seniority_allowed
    reason = (
        "Matched AI relevance and non-junior constraints."
        if passed
        else "Fallback rules rejected this role."
    )
    return {
        "is_ai_related": ai_related,
        "is_seniority_allowed": seniority_allowed,
        "passed": passed,
        "reason": reason,
    }
