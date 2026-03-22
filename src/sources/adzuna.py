import re
from datetime import date, datetime
from typing import Optional

import requests

from src.models import Job

_ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
_REMOTE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)


def build_search_queries(
    titles: list[str],
    country_codes: list[str],
    titles_per_query: int = 10,
) -> list[dict]:
    """Group job titles into OR-combined queries to stay within API call budget."""
    queries = []
    for i in range(0, len(titles), titles_per_query):
        batch = titles[i : i + titles_per_query]
        what = " OR ".join(f'"{t}"' for t in batch)
        for country in country_codes:
            queries.append({"country": country, "what": what})
    return queries


def normalize_adzuna_job(raw: dict) -> Job:
    title = raw.get("title", "")
    company = raw.get("company", {}).get("display_name", "Unknown")
    url = raw.get("redirect_url", "")
    location = raw.get("location", {}).get("display_name", "")
    description = raw.get("description", "")

    created_str = raw.get("created", "")
    posted_date: Optional[date] = None
    if created_str:
        try:
            posted_date = datetime.fromisoformat(created_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    salary_raw: Optional[str] = None
    if salary_min:
        salary_raw = f"€{salary_min:,.0f}" + (f"–€{salary_max:,.0f}" if salary_max else "")

    remote = bool(_REMOTE_PATTERN.search(location)) or bool(_REMOTE_PATTERN.search(title))

    return Job(
        title=title,
        company=company,
        url=url,
        location=location,
        description=description,
        source="adzuna",
        salary_raw=salary_raw,
        remote=remote,
        posted_date=posted_date,
    )


def fetch_adzuna_jobs(
    app_id: str,
    api_key: str,
    titles: list[str],
    country_codes: list[str],
    results_per_page: int = 50,
) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    queries = build_search_queries(titles, country_codes)

    for q in queries:
        country = q["country"]
        url = f"{_ADZUNA_BASE}/{country}/search/1"
        try:
            resp = requests.get(
                url,
                params={
                    "app_id": app_id,
                    "app_key": api_key,
                    "what": q["what"],
                    "results_per_page": results_per_page,
                    "content-type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            for result in resp.json().get("results", []):
                jobs.append(normalize_adzuna_job(result))
        except Exception as e:
            errors.append(f"Adzuna [{country}]: {e}")

    return jobs, errors
