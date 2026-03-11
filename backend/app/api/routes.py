from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import CrawlKeywordConfig, DismissedJob, FilteredJob, RawJob, SyncRun
from app.schemas import (
    JobItem,
    JobsResponse,
    KeywordSettingsResponse,
    KeywordSettingsUpdateRequest,
    StatsResponse,
    SyncRunItem,
    TriggerSyncResponse,
)
from app.services.pipeline import (
    DEFAULT_SEARCH_TERMS,
    get_stats,
    run_sync_pipeline,
    start_sync_pipeline_async,
)
from app.services.llm import DEFAULT_LLM_RULES


router = APIRouter()


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


@router.get("/jobs", response_model=JobsResponse)
def list_jobs(
    request: Request,
    view: Literal["filtered", "all", "dismissed"] = "filtered",
    session: Session = Depends(get_session),
) -> JobsResponse:
    if view == "filtered":
        query = (
            select(RawJob, FilteredJob.reason, DismissedJob.reason)
            .join(FilteredJob, FilteredJob.raw_job_id == RawJob.id)
            .outerjoin(
                DismissedJob,
                and_(
                    DismissedJob.site == RawJob.site,
                    DismissedJob.job_url == RawJob.job_url,
                    or_(
                        DismissedJob.date_posted == RawJob.date_posted,
                        DismissedJob.date_posted.is_(None),
                        RawJob.date_posted.is_(None),
                        and_(DismissedJob.date_posted.is_(None), RawJob.date_posted.is_(None)),
                    ),
                ),
            )
            .where(DismissedJob.id.is_(None))
            .order_by(
                RawJob.date_posted.desc().nullslast(),
                RawJob.created_at.desc(),
                RawJob.id.desc(),
            )
        )
        rows = session.execute(query).all()
        items = [
            JobItem(
                id=raw_job.id,
                site=raw_job.site,
                job_url=raw_job.job_url,
                title=raw_job.title,
                company=raw_job.company,
                location=raw_job.location,
                search_term=raw_job.search_term,
                date_posted=raw_job.date_posted,
                filter_reason=reason,
                dismiss_reason=dismiss_reason,
            )
            for raw_job, reason, dismiss_reason in rows
        ]
    elif view == "dismissed":
        query = (
            select(RawJob, DismissedJob.reason)
            .join(DismissedJob, DismissedJob.raw_job_id == RawJob.id)
            .order_by(
                RawJob.date_posted.desc().nullslast(),
                DismissedJob.dismissed_at.desc(),
                RawJob.id.desc(),
            )
        )
        rows = session.execute(query).all()
        items = [
            JobItem(
                id=raw_job.id,
                site=raw_job.site,
                job_url=raw_job.job_url,
                title=raw_job.title,
                company=raw_job.company,
                location=raw_job.location,
                search_term=raw_job.search_term,
                date_posted=raw_job.date_posted,
                dismiss_reason=dismiss_reason,
            )
            for raw_job, dismiss_reason in rows
        ]
    else:
        rows = session.execute(
            select(RawJob).order_by(
                RawJob.date_posted.desc().nullslast(),
                RawJob.created_at.desc(),
                RawJob.id.desc(),
            )
        ).scalars()
        items = [
            JobItem(
                id=raw_job.id,
                site=raw_job.site,
                job_url=raw_job.job_url,
                title=raw_job.title,
                company=raw_job.company,
                location=raw_job.location,
                search_term=raw_job.search_term,
                date_posted=raw_job.date_posted,
            )
            for raw_job in rows
        ]

    return JobsResponse(view=view, items=items)


@router.get("/jobs/{job_id}", response_model=JobItem)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobItem:
    raw_job = session.get(RawJob, job_id)
    if raw_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    reason = raw_job.filtered_job.reason if raw_job.filtered_job else None
    dismiss_reason = raw_job.dismissed_job.reason if raw_job.dismissed_job else None
    return JobItem(
        id=raw_job.id,
        site=raw_job.site,
        job_url=raw_job.job_url,
        title=raw_job.title,
        company=raw_job.company,
        location=raw_job.location,
        search_term=raw_job.search_term,
        date_posted=raw_job.date_posted,
        filter_reason=reason,
        dismiss_reason=dismiss_reason,
    )


@router.get("/stats", response_model=StatsResponse)
def stats(request: Request) -> StatsResponse:
    payload = get_stats(request.app.state.session_factory)
    return StatsResponse(**payload)


@router.get("/sync-runs", response_model=list[SyncRunItem])
def sync_runs(session: Session = Depends(get_session)) -> list[SyncRunItem]:
    runs = session.execute(select(SyncRun).order_by(SyncRun.id.desc()).limit(20)).scalars()
    return [
        SyncRunItem(
            id=run.id,
            status=run.status,
            attempt_count=run.attempt_count,
            jobs_fetched=run.jobs_fetched,
            jobs_inserted=run.jobs_inserted,
            jobs_evaluated=run.jobs_evaluated,
            jobs_filtered=run.jobs_filtered,
            total_keywords=run.total_keywords,
            completed_keywords=run.completed_keywords,
            current_stage=run.current_stage,
            current_keyword=run.current_keyword,
            progress_message=run.progress_message,
            error_message=run.error_message,
            started_at=run.started_at.isoformat(),
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
        )
        for run in runs
    ]


@router.post("/jobs/sync", response_model=TriggerSyncResponse)
def trigger_sync(request: Request) -> TriggerSyncResponse:
    sync_run_id = start_sync_pipeline_async(
        session_factory=request.app.state.session_factory,
        settings=request.app.state.settings,
    )
    return TriggerSyncResponse(sync_run_id=sync_run_id)


@router.get("/sync-runs/{sync_run_id}", response_model=SyncRunItem)
def get_sync_run(sync_run_id: int, session: Session = Depends(get_session)) -> SyncRunItem:
    run = session.get(SyncRun, sync_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return SyncRunItem(
        id=run.id,
        status=run.status,
        attempt_count=run.attempt_count,
        jobs_fetched=run.jobs_fetched,
        jobs_inserted=run.jobs_inserted,
        jobs_evaluated=run.jobs_evaluated,
        jobs_filtered=run.jobs_filtered,
        total_keywords=run.total_keywords,
        completed_keywords=run.completed_keywords,
        current_stage=run.current_stage,
        current_keyword=run.current_keyword,
        progress_message=run.progress_message,
        error_message=run.error_message,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )


@router.post("/jobs/{job_id}/dismiss")
def dismiss_job(job_id: int, session: Session = Depends(get_session)) -> dict[str, int]:
    raw_job = session.get(RawJob, job_id)
    if raw_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if raw_job.filtered_job is None:
        raise HTTPException(status_code=400, detail="Only filtered jobs can be dismissed")

    if raw_job.date_posted is None:
        date_clause = DismissedJob.date_posted.is_(None)
    else:
        date_clause = DismissedJob.date_posted == raw_job.date_posted

    existing = session.execute(
        select(DismissedJob).where(
            DismissedJob.site == raw_job.site,
            DismissedJob.job_url == raw_job.job_url,
            date_clause,
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            DismissedJob(
                raw_job_id=raw_job.id,
                site=raw_job.site,
                job_url=raw_job.job_url,
                date_posted=raw_job.date_posted,
                reason="dismissed by user",
            )
        )
        session.commit()

    return {"job_id": job_id}


@router.get("/settings/keywords", response_model=KeywordSettingsResponse)
def get_keyword_settings(session: Session = Depends(get_session)) -> KeywordSettingsResponse:
    config = session.execute(
        select(CrawlKeywordConfig).order_by(CrawlKeywordConfig.id.desc()).limit(1)
    ).scalar_one_or_none()
    if config is None:
        return KeywordSettingsResponse(keywords=DEFAULT_SEARCH_TERMS, llm_rules=DEFAULT_LLM_RULES)

    keywords = [
        config.keyword_1.strip() if config.keyword_1 else "",
        config.keyword_2.strip() if config.keyword_2 else "",
        config.keyword_3.strip() if config.keyword_3 else "",
        config.keyword_4.strip() if config.keyword_4 else "",
    ]
    llm_rules = [
        config.llm_rule_1.strip() if config.llm_rule_1 else "",
        config.llm_rule_2.strip() if config.llm_rule_2 else "",
        config.llm_rule_3.strip() if config.llm_rule_3 else "",
        config.llm_rule_4.strip() if config.llm_rule_4 else "",
    ]
    keywords = [item for item in keywords if item]
    llm_rules = [item for item in llm_rules if item]
    if not keywords:
        keywords = DEFAULT_SEARCH_TERMS
    if not llm_rules:
        llm_rules = DEFAULT_LLM_RULES
    return KeywordSettingsResponse(keywords=keywords, llm_rules=llm_rules)


@router.put("/settings/keywords", response_model=KeywordSettingsResponse)
def update_keyword_settings(
    payload: KeywordSettingsUpdateRequest,
    session: Session = Depends(get_session),
) -> KeywordSettingsResponse:
    keywords = [item.strip() for item in payload.keywords if item and item.strip()]
    if not keywords:
        raise HTTPException(status_code=400, detail="keywords cannot be empty")
    if len(keywords) > 4:
        raise HTTPException(status_code=400, detail="at most 4 keywords are allowed")
    llm_rules = [item.strip() for item in payload.llm_rules if item and item.strip()]
    if len(llm_rules) > 4:
        raise HTTPException(status_code=400, detail="at most 4 llm rules are allowed")
    if not llm_rules:
        llm_rules = DEFAULT_LLM_RULES.copy()

    while len(keywords) < 4:
        keywords.append("")
    while len(llm_rules) < 4:
        llm_rules.append("")

    config = session.execute(
        select(CrawlKeywordConfig).order_by(CrawlKeywordConfig.id.desc()).limit(1)
    ).scalar_one_or_none()
    if config is None:
        config = CrawlKeywordConfig(
            keyword_1=keywords[0] or None,
            keyword_2=keywords[1] or None,
            keyword_3=keywords[2] or None,
            keyword_4=keywords[3] or None,
            llm_rule_1=llm_rules[0] or None,
            llm_rule_2=llm_rules[1] or None,
            llm_rule_3=llm_rules[2] or None,
            llm_rule_4=llm_rules[3] or None,
        )
        session.add(config)
    else:
        config.keyword_1 = keywords[0] or None
        config.keyword_2 = keywords[1] or None
        config.keyword_3 = keywords[2] or None
        config.keyword_4 = keywords[3] or None
        config.llm_rule_1 = llm_rules[0] or None
        config.llm_rule_2 = llm_rules[1] or None
        config.llm_rule_3 = llm_rules[2] or None
        config.llm_rule_4 = llm_rules[3] or None

    session.commit()
    keyword_result = [item for item in keywords if item]
    llm_rule_result = [item for item in llm_rules if item]
    return KeywordSettingsResponse(keywords=keyword_result, llm_rules=llm_rule_result)
