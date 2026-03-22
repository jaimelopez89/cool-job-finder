import re
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.models import Job

_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


def _is_remote(text: str) -> bool:
    return bool(_REMOTE_RE.search(text))


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    # Try ISO format variants
    for suffix in ("T", " ", "Z"):
        if suffix in s:
            try:
                return datetime.fromisoformat(s.split("Z")[0].split("+")[0]).date()
            except ValueError:
                pass
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def fetch_greenhouse(company_slugs: list[str]) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    for slug in company_slugs:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for j in resp.json().get("jobs", []):
                location = j.get("location", {}).get("name", "")
                jobs.append(Job(
                    title=j.get("title", ""),
                    company=slug.replace("-", " ").title(),
                    url=j.get("absolute_url", ""),
                    location=location,
                    description=_strip_html(j.get("content", "")),
                    source="greenhouse",
                    remote=_is_remote(location) or _is_remote(j.get("title", "")),
                    # Greenhouse public API returns updated_at (last modified), not created_at.
                    # This means recently-edited old jobs may surface as new — acceptable for v1.
                    posted_date=_parse_date(j.get("updated_at")),
                ))
        except Exception as e:
            errors.append(f"Greenhouse [{slug}]: {e}")
    return jobs, errors


def fetch_lever(company_slugs: list[str]) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    for slug in company_slugs:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for j in resp.json():
                location = j.get("categories", {}).get("location", "")
                posted_ms = j.get("createdAt")
                posted_date = date.fromtimestamp(posted_ms / 1000) if posted_ms else None
                jobs.append(Job(
                    title=j.get("text", ""),
                    company=slug.replace("-", " ").title(),
                    url=j.get("hostedUrl", ""),
                    location=location,
                    description=j.get("descriptionPlain", ""),
                    source="lever",
                    remote=_is_remote(location) or _is_remote(j.get("text", "")),
                    posted_date=posted_date,
                ))
        except Exception as e:
            errors.append(f"Lever [{slug}]: {e}")
    return jobs, errors


def fetch_ashby(company_slugs: list[str]) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    for slug in company_slugs:
        url = f"https://api.ashbyhq.com/posting-public/job-board/{slug}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for j in resp.json().get("jobPostings", []):
                location = j.get("locationName", "")
                is_remote = j.get("isRemote", False)
                jobs.append(Job(
                    title=j.get("title", ""),
                    company=slug.replace("-", " ").title(),
                    url=j.get("jobUrl", ""),
                    location="Remote" if is_remote else location,
                    description=_strip_html(j.get("descriptionHtml", "")),
                    source="ashby",
                    remote=is_remote,
                    posted_date=_parse_date(j.get("updatedAt")),
                ))
        except Exception as e:
            errors.append(f"Ashby [{slug}]: {e}")
    return jobs, errors
