from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

import pandas as pd

from app.services.jobspy_loader import load_scrape_jobs


class LinkedInScraperService:
    def __init__(
        self,
        *,
        search_terms: Sequence[str],
        location: str = "Hong Kong",
        hours_old: int = 24,
        results_wanted: int = 50,
        site_name: Sequence[str] | None = None,
        verbose: int = 1,
        linkedin_fetch_description: bool = True,
    ) -> None:
        self.search_terms = list(search_terms)
        self.location = location
        self.hours_old = hours_old
        self.results_wanted = results_wanted
        self.site_name = list(site_name or ["linkedin"])
        self.verbose = verbose
        self.linkedin_fetch_description = linkedin_fetch_description

    def scrape(
        self,
        *,
        scrape_callable: Callable[..., pd.DataFrame] | None = None,
        progress_callback: Callable[..., None] | None = None,
    ) -> list[dict[str, Any]]:
        scrape_jobs = scrape_callable or load_scrape_jobs()
        all_jobs: list[pd.DataFrame] = []
        total_keywords = len(self.search_terms)

        for index, term in enumerate(self.search_terms, start=1):
            if progress_callback:
                progress_callback(
                    keyword=term,
                    completed_keywords=index - 1,
                    total_keywords=total_keywords,
                    message=f"Scraping keyword {index}/{total_keywords}: {term}",
                )
            jobs = scrape_jobs(
                site_name=self.site_name,
                search_term=term,
                location=self.location,
                results_wanted=self.results_wanted,
                hours_old=self.hours_old,
                verbose=self.verbose,
                linkedin_fetch_description=self.linkedin_fetch_description,
            )
            if len(jobs) == 0:
                if progress_callback:
                    progress_callback(
                        keyword=term,
                        completed_keywords=index,
                        total_keywords=total_keywords,
                        message=f"Keyword {term} finished: 0 results",
                    )
                continue

            jobs = jobs.copy()
            jobs["search_term"] = term
            all_jobs.append(jobs)
            if progress_callback:
                progress_callback(
                    keyword=term,
                    completed_keywords=index,
                    total_keywords=total_keywords,
                    message=f"Keyword {term} finished: {len(jobs)} results",
                )

        if not all_jobs:
            return []

        merged = pd.concat(all_jobs, ignore_index=True)
        if "date_posted" in merged.columns:
            merged["date_posted"] = merged["date_posted"].apply(_normalize_date)

        dedup_columns = ["job_url"]
        if "date_posted" in merged.columns:
            dedup_columns.append("date_posted")
        merged = merged.drop_duplicates(subset=dedup_columns, keep="first")

        return merged.to_dict(orient="records")


def _normalize_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()
