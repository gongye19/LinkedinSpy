from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RawJob


class RawJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_get(self, payload: Mapping[str, Any]) -> RawJob:
        raw_job, _created = self.create_or_get_with_flag(payload)
        return raw_job

    def create_or_get_with_flag(self, payload: Mapping[str, Any]) -> tuple[RawJob, bool]:
        existing = self.session.execute(
            select(RawJob).where(
                RawJob.site == payload["site"],
                RawJob.job_url == payload["job_url"],
                RawJob.date_posted == payload.get("date_posted"),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False

        raw_job = RawJob(
            site=str(payload["site"]),
            job_url=str(payload["job_url"]),
            title=str(payload["title"]),
            company=_to_optional_string(payload.get("company")),
            location=_to_optional_string(payload.get("location")),
            description=_to_optional_string(payload.get("description")),
            search_term=_to_optional_string(payload.get("search_term")),
            date_posted=_to_optional_date(payload.get("date_posted")),
        )
        self.session.add(raw_job)
        self.session.flush()
        return raw_job, True


def _to_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_optional_date(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    raise TypeError(f"Unsupported date value: {value!r}")
