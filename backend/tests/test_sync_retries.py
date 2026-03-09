from app.db import create_session_factory, init_db
from app.models import SyncRun
from app.services.sync import SyncService


def test_sync_records_failure_after_retries_exhausted(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    attempts = {"count": 0}

    def always_fail(_sync_run_id: int, _progress_updater) -> None:
        attempts["count"] += 1
        raise RuntimeError("linkedin blocked")

    service = SyncService(
        session_factory=session_factory,
        max_attempts=3,
        sleep_func=lambda _seconds: None,
    )

    sync_run_id = service.run(job_fetcher=always_fail)

    with session_factory() as session:
        sync_run = session.get(SyncRun, sync_run_id)

        assert sync_run is not None
        assert sync_run.status == "failed"
        assert sync_run.attempt_count == 3
        assert sync_run.error_message == "linkedin blocked"
        assert attempts["count"] == 3
