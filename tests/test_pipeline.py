import pytest
from unittest.mock import MagicMock, patch
from src.models import Job
from run import deduplicate_jobs, run_pipeline


def make_job(url="https://example.com/1", company="Acme", title="VP Marketing", posted_date=None):
    return Job(title=title, company=company, url=url, location="Remote",
               description="Test.", source="adzuna", posted_date=posted_date)


def test_deduplicate_removes_same_url():
    jobs = [make_job(url="https://a.com/1"), make_job(url="https://a.com/1")]
    result = deduplicate_jobs(jobs)
    assert len(result) == 1


def test_deduplicate_removes_same_content():
    # Same company+title+date, different URLs
    j1 = make_job(url="https://a.com/1", company="TechCo", title="CMO")
    j2 = make_job(url="https://b.com/2", company="TechCo", title="CMO")
    result = deduplicate_jobs([j1, j2])
    assert len(result) == 1


def test_deduplicate_keeps_different_jobs():
    j1 = make_job(url="https://a.com/1", title="VP Marketing")
    j2 = make_job(url="https://b.com/2", title="CMO", company="OtherCo")
    result = deduplicate_jobs([j1, j2])
    assert len(result) == 2
