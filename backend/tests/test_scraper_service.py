from datetime import date

import pandas as pd

from app.services.scraper import LinkedInScraperService


def test_scraper_merges_keywords_and_deduplicates_on_url_and_date():
    def fake_scrape(*, search_term: str, **_: object) -> pd.DataFrame:
        if search_term == "ai engineer":
            return pd.DataFrame(
                [
                    {
                        "site": "linkedin",
                        "job_url": "https://www.linkedin.com/jobs/view/1",
                        "title": "AI Engineer",
                        "company": "Acme",
                        "date_posted": date(2026, 3, 8),
                    },
                    {
                        "site": "linkedin",
                        "job_url": "https://www.linkedin.com/jobs/view/2",
                        "title": "LLM Engineer",
                        "company": "Beta",
                        "date_posted": date(2026, 3, 8),
                    },
                ]
            )

        return pd.DataFrame(
            [
                {
                    "site": "linkedin",
                    "job_url": "https://www.linkedin.com/jobs/view/1",
                    "title": "AI Engineer",
                    "company": "Acme",
                    "date_posted": date(2026, 3, 8),
                },
                {
                    "site": "linkedin",
                    "job_url": "https://www.linkedin.com/jobs/view/1",
                    "title": "AI Engineer",
                    "company": "Acme",
                    "date_posted": date(2026, 3, 9),
                },
            ]
        )

    service = LinkedInScraperService(search_terms=["ai engineer", "llm"])

    jobs = service.scrape(scrape_callable=fake_scrape)

    assert len(jobs) == 3
    assert {job["search_term"] for job in jobs} == {"ai engineer", "llm"}
    assert sum(1 for job in jobs if job["job_url"].endswith("/1")) == 2
