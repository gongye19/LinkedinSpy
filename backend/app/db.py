from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


@dataclass
class SessionFactory:
    engine: Engine
    _sessionmaker: sessionmaker[Session]

    def __call__(self) -> Session:
        return self._sessionmaker()


def create_session_factory(database_url: str) -> SessionFactory:
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, future=True, connect_args=connect_args)
    return SessionFactory(
        engine=engine,
        _sessionmaker=sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True),
    )


def init_db(engine: Engine) -> None:
    from app.models import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)
    # SQLite needs lightweight in-place schema evolution for existing local files.
    # For Postgres on Railway, table creation is handled by metadata and these
    # PRAGMA/ALTER statements are not applicable.
    if engine.dialect.name == "sqlite":
        _ensure_keyword_columns(engine)
    elif engine.dialect.name == "postgresql":
        _ensure_postgres_sequences(engine)


def _ensure_keyword_columns(engine: Engine) -> None:
    with engine.begin() as conn:
        info_rows = conn.execute(text("PRAGMA table_info(crawl_keyword_configs)")).fetchall()
        if not info_rows:
            _ensure_sync_run_columns(conn)
            return
        column_names = {row[1] for row in info_rows}
        if "keyword_4" not in column_names:
            conn.execute(text("ALTER TABLE crawl_keyword_configs ADD COLUMN keyword_4 VARCHAR(128)"))
        _ensure_sync_run_columns(conn)


def _ensure_sync_run_columns(conn) -> None:
    info_rows = conn.execute(text("PRAGMA table_info(sync_runs)")).fetchall()
    if not info_rows:
        return
    column_names = {row[1] for row in info_rows}
    if "total_keywords" not in column_names:
        conn.execute(text("ALTER TABLE sync_runs ADD COLUMN total_keywords INTEGER DEFAULT 0 NOT NULL"))
    if "completed_keywords" not in column_names:
        conn.execute(text("ALTER TABLE sync_runs ADD COLUMN completed_keywords INTEGER DEFAULT 0 NOT NULL"))
    if "current_stage" not in column_names:
        conn.execute(text("ALTER TABLE sync_runs ADD COLUMN current_stage VARCHAR(64)"))
    if "current_keyword" not in column_names:
        conn.execute(text("ALTER TABLE sync_runs ADD COLUMN current_keyword VARCHAR(128)"))
    if "progress_message" not in column_names:
        conn.execute(text("ALTER TABLE sync_runs ADD COLUMN progress_message TEXT"))

    dismissed_rows = conn.execute(text("PRAGMA table_info(dismissed_jobs)")).fetchall()
    if dismissed_rows:
        dismissed_columns = {row[1] for row in dismissed_rows}
        if "site" not in dismissed_columns:
            conn.execute(text("ALTER TABLE dismissed_jobs ADD COLUMN site VARCHAR(64)"))
        if "job_url" not in dismissed_columns:
            conn.execute(text("ALTER TABLE dismissed_jobs ADD COLUMN job_url VARCHAR(1024)"))
        if "date_posted" not in dismissed_columns:
            conn.execute(text("ALTER TABLE dismissed_jobs ADD COLUMN date_posted DATE"))
        conn.execute(
            text(
                """
                UPDATE dismissed_jobs
                SET site = COALESCE(site, (SELECT site FROM raw_jobs WHERE raw_jobs.id = dismissed_jobs.raw_job_id)),
                    job_url = COALESCE(job_url, (SELECT job_url FROM raw_jobs WHERE raw_jobs.id = dismissed_jobs.raw_job_id)),
                    date_posted = COALESCE(date_posted, (SELECT date_posted FROM raw_jobs WHERE raw_jobs.id = dismissed_jobs.raw_job_id))
                """
            )
        )


def _ensure_postgres_sequences(engine: Engine) -> None:
    table_id_columns = (
        ("raw_jobs", "id"),
        ("job_evaluations", "id"),
        ("filtered_jobs", "id"),
        ("sync_runs", "id"),
        ("dismissed_jobs", "id"),
        ("crawl_keyword_configs", "id"),
    )
    with engine.begin() as conn:
        for table_name, id_column in table_id_columns:
            conn.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', '{id_column}'),
                        COALESCE((SELECT MAX({id_column}) FROM {table_name}), 0) + 1,
                        false
                    )
                    """
                )
            )
