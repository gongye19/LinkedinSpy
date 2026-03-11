from datetime import date

from app.services.pipeline import _filter_jobs_with_known_date


def test_filter_jobs_with_known_date_skips_unknown_dates():
    jobs = [
        {"job_url": "https://example.com/1", "date_posted": date(2026, 3, 11)},
        {"job_url": "https://example.com/2", "date_posted": None},
        {"job_url": "https://example.com/3", "date_posted": "NaT"},
        {"job_url": "https://example.com/4", "date_posted": "2026-03-10"},
    ]

    filtered = _filter_jobs_with_known_date(jobs)

    assert len(filtered) == 2
    assert filtered[0]["job_url"] == "https://example.com/1"
    assert filtered[0]["date_posted"] == date(2026, 3, 11)
    assert filtered[1]["job_url"] == "https://example.com/4"
    assert filtered[1]["date_posted"] == date(2026, 3, 10)
