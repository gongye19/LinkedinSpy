from app.config import get_settings
from app.db import create_session_factory, init_db
from app.services.pipeline import run_sync_pipeline


def run_sync_once() -> int:
    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    init_db(session_factory.engine)
    return run_sync_pipeline(session_factory=session_factory, settings=settings)


if __name__ == "__main__":
    sync_run_id = run_sync_once()
    print(f"sync_run_id={sync_run_id}")
