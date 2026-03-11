from datetime import date

from fastapi.testclient import TestClient

from app.db import create_session_factory, init_db
from app.main import create_app
from app.models import FilteredJob, RawJob


def test_jobs_endpoint_defaults_to_filtered_view(tmp_path):
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
        session.add(FilteredJob(raw_job_id=raw_job.id, reason="AI-related and not junior"))
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["view"] == "filtered"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "AI Platform Engineer"


def test_jobs_endpoint_has_cors_headers(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/api/jobs", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_dismiss_job_moves_it_out_of_filtered_list(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    raw_job_id = None
    with session_factory() as session:
        raw_job = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/3",
            title="AI Research Engineer",
            company="Gamma",
            date_posted=date(2026, 3, 8),
        )
        session.add(raw_job)
        session.commit()
        session.refresh(raw_job)
        raw_job_id = raw_job.id
        session.add(FilteredJob(raw_job_id=raw_job.id, reason="AI-related and not junior"))
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    dismiss_response = client.post(f"/api/jobs/{raw_job_id}/dismiss")
    assert dismiss_response.status_code == 200

    filtered_response = client.get("/api/jobs?view=filtered")
    dismissed_response = client.get("/api/jobs?view=dismissed")

    assert filtered_response.status_code == 200
    assert dismissed_response.status_code == 200
    assert len(filtered_response.json()["items"]) == 0
    assert len(dismissed_response.json()["items"]) == 1


def test_filtered_list_keeps_older_non_dismissed_jobs(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    with session_factory() as session:
        old_job = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/old",
            title="AI Engineer Old",
            company="Acme",
            date_posted=date(2026, 3, 8),
        )
        new_job = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/new",
            title="AI Engineer New",
            company="Acme",
            date_posted=date(2026, 3, 9),
        )
        session.add_all([old_job, new_job])
        session.commit()
        session.refresh(old_job)
        session.refresh(new_job)
        session.add(FilteredJob(raw_job_id=old_job.id, reason="pass"))
        session.add(FilteredJob(raw_job_id=new_job.id, reason="pass"))
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.get("/api/jobs?view=filtered")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["title"] == "AI Engineer New"
    assert items[1]["title"] == "AI Engineer Old"


def test_dismissed_job_reappears_only_when_new_date_posted(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    old_post_id = None
    with session_factory() as session:
        old_post = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/same",
            title="AI Engineer Old Posting",
            company="Acme",
            date_posted=date(2026, 3, 8),
        )
        new_post = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/same",
            title="AI Engineer Reposted",
            company="Acme",
            date_posted=date(2026, 3, 9),
        )
        session.add_all([old_post, new_post])
        session.commit()
        session.refresh(old_post)
        session.refresh(new_post)
        old_post_id = old_post.id
        session.add(FilteredJob(raw_job_id=old_post.id, reason="pass"))
        session.add(FilteredJob(raw_job_id=new_post.id, reason="pass"))
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    dismiss_response = client.post(f"/api/jobs/{old_post_id}/dismiss")
    assert dismiss_response.status_code == 200

    response = client.get("/api/jobs?view=filtered")
    assert response.status_code == 200
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["title"] == "AI Engineer Reposted"


def test_dismissed_job_not_recommended_when_new_scrape_missing_date(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)

    dismissed_id = None
    with session_factory() as session:
        dismissed = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/same-missing-date",
            title="AI Engineer Original",
            company="Acme",
            date_posted=date(2026, 3, 8),
        )
        missing_date = RawJob(
            site="linkedin",
            job_url="https://www.linkedin.com/jobs/view/same-missing-date",
            title="AI Engineer Missing Date",
            company="Acme",
            date_posted=None,
        )
        session.add_all([dismissed, missing_date])
        session.commit()
        session.refresh(dismissed)
        session.refresh(missing_date)
        dismissed_id = dismissed.id
        session.add(FilteredJob(raw_job_id=dismissed.id, reason="pass"))
        session.add(FilteredJob(raw_job_id=missing_date.id, reason="pass"))
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    dismiss_response = client.post(f"/api/jobs/{dismissed_id}/dismiss")
    assert dismiss_response.status_code == 200

    response = client.get("/api/jobs?view=filtered")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 0
