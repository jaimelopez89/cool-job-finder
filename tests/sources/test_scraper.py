import pytest
from unittest.mock import patch, MagicMock
from src.sources.scraper import scrape_career_page, find_job_links


def _mock_response(html: str):
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


SAMPLE_HTML = """
<html><body>
  <a href="/careers/vp-marketing">VP Marketing - Remote</a>
  <a href="/careers/cmo">Chief Marketing Officer - Helsinki</a>
  <a href="/about">About us</a>
</body></html>
"""


def test_find_job_links_filters_career_links():
    links = find_job_links(SAMPLE_HTML, base_url="https://example.com", company_careers_url="https://example.com/careers")
    assert len(links) == 2
    assert all("careers" in link for link in links)


def test_scrape_returns_jobs_for_matching_titles(mocker):
    mocker.patch("requests.get", return_value=_mock_response(SAMPLE_HTML))
    jobs, errors = scrape_career_page(
        name="Example Corp",
        careers_url="https://example.com/careers",
        target_titles=["VP Marketing", "CMO", "Chief Marketing Officer"],
    )
    assert len(jobs) >= 1
    assert all(j.source == "scraper" for j in jobs)
    assert errors == []


def test_scrape_handles_request_error(mocker):
    mocker.patch("requests.get", side_effect=Exception("Timeout"))
    jobs, errors = scrape_career_page(
        name="Broken Corp",
        careers_url="https://broken.example.com/careers",
        target_titles=["VP Marketing"],
    )
    assert jobs == []
    assert len(errors) == 1
