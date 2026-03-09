from datetime import date

from app.db import create_session_factory, init_db
from app.models import FilteredJob, RawJob
from app.services.filtering import JobFilteringService


def test_filtering_rejects_entry_level_jobs(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    with session_factory() as session:
        raw_job = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/1",
            title="Junior AI Engineer",
            company="Acme",
            date_posted=date(2026, 3, 8),
        )
        session.add(raw_job)
        session.commit()
        session.refresh(raw_job)

        service = JobFilteringService(session=session, model_name="test-model")
        evaluation = service.evaluate_and_store(
            raw_job,
            evaluator=lambda _payload: {
                "is_ai_related": True,
                "is_seniority_allowed": False,
                "passed": False,
                "reason": "Role is explicitly junior level.",
            },
        )

        assert evaluation.passed is False
        assert session.query(FilteredJob).count() == 0


def test_filtering_promotes_passing_jobs(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    with session_factory() as session:
        raw_job = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/2",
            title="AI Platform Engineer",
            company="Beta",
            date_posted=date(2026, 3, 8),
        )
        session.add(raw_job)
        session.commit()
        session.refresh(raw_job)

        service = JobFilteringService(session=session, model_name="test-model")
        evaluation = service.evaluate_and_store(
            raw_job,
            evaluator=lambda _payload: {
                "is_ai_related": True,
                "is_seniority_allowed": True,
                "passed": True,
                "reason": "The role focuses on AI platform delivery.",
            },
        )

        assert evaluation.passed is True
        assert session.query(FilteredJob).count() == 1
