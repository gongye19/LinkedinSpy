from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FilteredJob, JobEvaluation, RawJob


class JobFilteringService:
    def __init__(self, *, session: Session, model_name: str) -> None:
        self.session = session
        self.model_name = model_name

    def evaluate_and_store(
        self,
        raw_job: RawJob,
        *,
        evaluator: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> JobEvaluation:
        existing = self.session.execute(
            select(JobEvaluation)
            .where(JobEvaluation.raw_job_id == raw_job.id)
            .order_by(JobEvaluation.id.desc())
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        payload = {
            "title": raw_job.title,
            "company": raw_job.company,
            "location": raw_job.location,
            "description": raw_job.description,
            "search_term": raw_job.search_term,
            "job_url": raw_job.job_url,
        }
        result = self._safe_evaluate(payload, evaluator)
        evaluation = JobEvaluation(
            raw_job_id=raw_job.id,
            is_ai_related=bool(result["is_ai_related"]),
            is_seniority_allowed=bool(result["is_seniority_allowed"]),
            passed=bool(result["passed"]),
            reason=str(result["reason"]),
            model_name=self.model_name,
        )
        self.session.add(evaluation)
        self.session.flush()

        if evaluation.passed and raw_job.filtered_job is None:
            self.session.add(FilteredJob(raw_job_id=raw_job.id, reason=evaluation.reason))

        self.session.commit()
        self.session.refresh(evaluation)
        return evaluation

    def _safe_evaluate(
        self,
        payload: dict[str, Any],
        evaluator: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            return evaluator(payload)
        except Exception as exc:
            # Keep pipeline resilient when external LLM has transient failures.
            text = " ".join(str(payload.get(key, "") or "") for key in ("title", "description", "search_term")).lower()
            ai_related = any(token in text for token in ("ai", "llm", "rag", "agent"))
            seniority_allowed = not any(token in text for token in ("junior", "entry level"))
            passed = ai_related and seniority_allowed
            return {
                "is_ai_related": ai_related,
                "is_seniority_allowed": seniority_allowed,
                "passed": passed,
                "reason": f"LLM timeout/error fallback: {exc}",
            }
