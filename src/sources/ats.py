import json
import re
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.models import Job

_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
_UA = {"User-Agent": "Mozilla/5.0 (compatible; job-finder-bot/1.0)"}

# Title keywords mirrored from run.py prefilter — used inside fetch_ashby
# to avoid fetching description pages for irrelevant postings.
_FUNCTION_KW = {
    "marketing", "growth", "revenue", "demand", "generation",
    "gtm", "go-to-market", "brand", "content", "communications",
    "excellence", "developer relations", "devrel", "portfolio",
    "product management", "product strategy", "product marketing",
    "field marketing", "market",
}
_CSUITE_KW = {"cmo", "cpo", "cgo", "cto", "cro"}


def _is_remote(text: str) -> bool:
    return bool(_REMOTE_RE.search(text))


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
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


def _title_matches(title: str) -> bool:
    """Return True if the job title looks like a target marketing/product role."""
    tl = title.lower()
    if any(kw in tl for kw in _FUNCTION_KW):
        return True
    return any(tl == kw or f" {kw}" in tl or tl.startswith(kw) for kw in _CSUITE_KW)


def _extract_ashby_appdata(html: str) -> Optional[dict]:
    """Extract window.__appData JSON from an Ashby job board page."""
    m = re.search(r"window\.__appData\s*=\s*(\{)", html)
    if not m:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html, m.start(1))
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def fetch_greenhouse(company_slugs: list[str]) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    for slug in company_slugs:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            company_name = data.get("company", {}).get("name") or slug.replace("-", " ").title()
            for j in data.get("jobs", []):
                location = j.get("location", {}).get("name", "")
                jobs.append(Job(
                    title=j.get("title", ""),
                    company=company_name,
                    url=j.get("absolute_url", ""),
                    location=location,
                    description=_strip_html(j.get("content", "")),
                    source="greenhouse",
                    remote=_is_remote(location) or _is_remote(j.get("title", "")),
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
    """Scrape Ashby job boards via jobs.ashbyhq.com/{slug} (public HTML, no auth needed).

    Two-step: fetch board listing for titles → filter by target role → fetch
    description page only for matching postings (avoids N requests per company).
    """
    jobs: list[Job] = []
    errors: list[str] = []

    for slug in company_slugs:
        board_url = f"https://jobs.ashbyhq.com/{slug}"
        try:
            resp = requests.get(board_url, headers=_UA, timeout=15)
            resp.raise_for_status()
            data = _extract_ashby_appdata(resp.text)
            if data is None:
                errors.append(f"Ashby [{slug}]: could not parse __appData from page")
                continue

            org = data.get("organization", {})
            company_name = org.get("name") or slug.replace("-", " ").title()
            board_slug = org.get("hostedJobsPageSlug") or slug
            postings = data.get("jobBoard", {}).get("jobPostings", [])

            for j in postings:
                if not j.get("isListed", True):
                    continue
                title = j.get("title", "")
                if not _title_matches(title):
                    continue

                location = j.get("locationName", "")
                workplace = (j.get("workplaceType") or "").lower()
                is_remote = workplace == "remote" or _is_remote(location)
                job_id = j.get("id", "")
                job_url = f"https://jobs.ashbyhq.com/{board_slug}/{job_id}"

                # Fetch description from the individual posting page
                description = ""
                if job_id:
                    try:
                        jresp = requests.get(job_url, headers=_UA, timeout=10)
                        jdata = _extract_ashby_appdata(jresp.text)
                        if jdata:
                            desc_html = jdata.get("posting", {}).get("descriptionHtml", "")
                            description = _strip_html(desc_html)
                    except Exception:
                        pass  # Description missing is acceptable; scoring will note it

                jobs.append(Job(
                    title=title,
                    company=company_name,
                    url=job_url,
                    location="Remote" if is_remote else location,
                    description=description,
                    source="ashby",
                    remote=is_remote,
                    posted_date=_parse_date(j.get("publishedDate") or j.get("updatedAt")),
                ))

        except Exception as e:
            errors.append(f"Ashby [{slug}]: {e}")

    return jobs, errors
