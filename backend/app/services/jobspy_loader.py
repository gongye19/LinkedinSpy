from collections.abc import Callable
from typing import Any


def load_scrape_jobs() -> Callable[..., Any]:
    from jobspy import scrape_jobs

    return scrape_jobs
