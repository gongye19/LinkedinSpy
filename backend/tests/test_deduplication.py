from datetime import date

from app.db import create_session_factory, init_db
from app.models import RawJob
from app.repositories import RawJobRepository


def test_same_job_url_with_different_date_posted_is_kept(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    with session_factory() as session:
        repository = RawJobRepository(session)

        first = repository.create_or_get(
            {
                "site": "linkedin",
                "job_url": "https://www.linkedin.com/jobs/view/1",
                "title": "AI Engineer",
                "company": "Acme",
                "date_posted": date(2026, 3, 8),
            }
        )
        second = repository.create_or_get(
            {
                "site": "linkedin",
                "job_url": "https://www.linkedin.com/jobs/view/1",
                "title": "AI Engineer",
                "company": "Acme",
                "date_posted": date(2026, 3, 9),
            }
        )

        assert first.id != second.id
        assert session.query(RawJob).count() == 2


def test_same_job_url_with_same_date_posted_is_deduplicated(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    with session_factory() as session:
        repository = RawJobRepository(session)

        first = repository.create_or_get(
            {
                "site": "linkedin",
                "job_url": "https://www.linkedin.com/jobs/view/1",
                "title": "AI Engineer",
                "company": "Acme",
                "date_posted": date(2026, 3, 8),
            }
        )
        second = repository.create_or_get(
            {
                "site": "linkedin",
                "job_url": "https://www.linkedin.com/jobs/view/1",
                "title": "AI Engineer",
                "company": "Acme",
                "date_posted": date(2026, 3, 8),
            }
        )

        assert first.id == second.id
        assert session.query(RawJob).count() == 1
