import pytest
from unittest.mock import patch, MagicMock
from src.sources.adzuna import build_search_queries, fetch_adzuna_jobs, normalize_adzuna_job


def test_build_search_queries_groups_titles():
    titles = ["VP Marketing", "CMO", "Head of Marketing", "VP Growth"]
    country_codes = ["gb", "fi"]
    queries = build_search_queries(titles, country_codes, titles_per_query=2)
    # 2 titles per query → 2 query groups × 2 countries = 4 requests
    assert len(queries) == 4
    for q in queries:
        assert "country" in q
        assert "what" in q


def test_normalize_adzuna_job():
    raw = {
        "title": "VP Marketing",
        "company": {"display_name": "TechCo"},
        "redirect_url": "https://api.adzuna.com/redirect/123",
        "location": {"display_name": "Remote"},
        "description": "Lead our marketing team.",
        "created": "2026-03-20T10:00:00Z",
        "salary_min": 130000,
        "salary_max": 150000,
    }
    job = normalize_adzuna_job(raw)
    assert job.title == "VP Marketing"
    assert job.company == "TechCo"
    assert job.source == "adzuna"
    assert "130" in (job.salary_raw or "")


def test_normalize_adzuna_job_no_salary():
    raw = {
        "title": "CMO",
        "company": {"display_name": "Acme"},
        "redirect_url": "https://api.adzuna.com/redirect/456",
        "location": {"display_name": "Helsinki, Finland"},
        "description": "Chief Marketing role.",
        "created": "2026-03-21T08:00:00Z",
    }
    job = normalize_adzuna_job(raw)
    assert job.salary_raw is None


def test_fetch_adzuna_jobs_handles_api_error(mocker):
    mocker.patch("requests.get", side_effect=Exception("Connection error"))
    jobs, errors = fetch_adzuna_jobs(
        app_id="fake", api_key="fake",
        titles=["VP Marketing"], country_codes=["gb"]
    )
    assert jobs == []
    assert len(errors) > 0
