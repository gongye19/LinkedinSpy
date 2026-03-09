from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class RawJob(Base):
    __tablename__ = "raw_jobs"
    __table_args__ = (
        UniqueConstraint("site", "job_url", "date_posted", name="uq_raw_job_site_url_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site: Mapped[str] = mapped_column(String(64), nullable=False)
    job_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    search_term: Mapped[str | None] = mapped_column(String(255))
    date_posted: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    evaluations: Mapped[list["JobEvaluation"]] = relationship(back_populates="raw_job")
    filtered_job: Mapped["FilteredJob | None"] = relationship(back_populates="raw_job")
    dismissed_job: Mapped["DismissedJob | None"] = relationship(back_populates="raw_job")


class JobEvaluation(Base):
    __tablename__ = "job_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), nullable=False, index=True)
    is_ai_related: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_seniority_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    raw_job: Mapped[RawJob] = relationship(back_populates="evaluations")


class FilteredJob(Base):
    __tablename__ = "filtered_jobs"
    __table_args__ = (
        UniqueConstraint("raw_job_id", name="uq_filtered_job_raw_job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    raw_job: Mapped[RawJob] = relationship(back_populates="filtered_job")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_filtered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_keywords: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_keywords: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(64))
    current_keyword: Mapped[str | None] = mapped_column(String(128))
    progress_message: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DismissedJob(Base):
    __tablename__ = "dismissed_jobs"
    __table_args__ = (
        UniqueConstraint("site", "job_url", "date_posted", name="uq_dismissed_job_site_url_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), nullable=False, index=True)
    site: Mapped[str] = mapped_column(String(64), nullable=False)
    job_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    date_posted: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    raw_job: Mapped[RawJob] = relationship(back_populates="dismissed_job")


class CrawlKeywordConfig(Base):
    __tablename__ = "crawl_keyword_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_1: Mapped[str | None] = mapped_column(String(128))
    keyword_2: Mapped[str | None] = mapped_column(String(128))
    keyword_3: Mapped[str | None] = mapped_column(String(128))
    keyword_4: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
