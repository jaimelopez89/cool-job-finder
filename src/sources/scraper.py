import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.models import Job

_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)


def find_job_links(html: str, base_url: str, company_careers_url: str) -> list[str]:
    """Extract links from careers page that look like job postings."""
    soup = BeautifulSoup(html, "html.parser")
    careers_path = urlparse(company_careers_url).path.rstrip("/")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.netloc == urlparse(base_url).netloc and parsed.path.startswith(careers_path + "/"):
            links.append(href)
    return list(set(links))


def _title_matches(link_text: str, target_titles: list[str]) -> bool:
    text_lower = link_text.lower()
    return any(t.lower() in text_lower for t in target_titles)


def scrape_career_page(
    name: str,
    careers_url: str,
    target_titles: list[str],
) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []

    try:
        resp = requests.get(careers_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        base_url = f"{urlparse(careers_url).scheme}://{urlparse(careers_url).netloc}"

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not _title_matches(text, target_titles):
                continue
            href = urljoin(base_url, a["href"])
            jobs.append(Job(
                title=text,
                company=name,
                url=href,
                location="Remote" if _REMOTE_RE.search(text) else "See posting",
                description=f"See full job description at: {href}",
                source="scraper",
                remote=bool(_REMOTE_RE.search(text)),
            ))
    except Exception as e:
        errors.append(f"Scraper [{name}]: {e}")

    return jobs, errors
