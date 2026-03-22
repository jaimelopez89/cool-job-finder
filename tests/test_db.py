import pytest
import sqlite3
import tempfile
import os
from datetime import date
from src.db import init_db, insert_job, is_duplicate, update_job_field, get_jobs, insert_run
from src.models import Job


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_jobs.db")
    init_db(path)
    return path


def make_job(**kwargs):
    defaults = dict(
        title="VP Marketing",
        company="Acme",
        url="https://acme.com/jobs/1",
        location="Remote",
        description="Great role.",
        source="adzuna",
    )
    defaults.update(kwargs)
    return Job(**defaults)


def test_init_creates_tables(db_path):
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "jobs" in tables
    assert "runs" in tables
    conn.close()


def test_insert_job(db_path):
    job = make_job()
    insert_job(db_path, job, score=75, fit_summary="Good fit.", red_flags="", salary_estimate="", geo_bucket="remote")
    jobs = get_jobs(db_path)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "VP Marketing"


def test_is_duplicate_by_url(db_path):
    job = make_job()
    insert_job(db_path, job, score=75, fit_summary="", red_flags="", salary_estimate="", geo_bucket="remote")
    assert is_duplicate(db_path, url=job.url, content_hash="different_hash") is True


def test_is_duplicate_by_hash(db_path):
    job = make_job()
    insert_job(db_path, job, score=75, fit_summary="", red_flags="", salary_estimate="", geo_bucket="remote")
    # Different URL, same content hash
    assert is_duplicate(db_path, url="https://other.com/jobs/99", content_hash=_content_hash(job)) is True


def test_not_duplicate_new_job(db_path):
    job = make_job()
    assert is_duplicate(db_path, url=job.url, content_hash="abc123") is False


def test_update_applied(db_path):
    job = make_job()
    insert_job(db_path, job, score=75, fit_summary="", red_flags="", salary_estimate="", geo_bucket="remote")
    jobs = get_jobs(db_path)
    job_id = jobs[0]["id"]
    update_job_field(db_path, job_id, "applied", True)
    updated = get_jobs(db_path)
    assert updated[0]["applied"] == 1


def test_update_dismissed(db_path):
    job = make_job()
    insert_job(db_path, job, score=75, fit_summary="", red_flags="", salary_estimate="", geo_bucket="remote")
    jobs = get_jobs(db_path)
    update_job_field(db_path, jobs[0]["id"], "dismissed", True)
    updated = get_jobs(db_path)
    assert updated[0]["dismissed"] == 1


def test_insert_run(db_path):
    insert_run(db_path, jobs_fetched=100, new_jobs=10, scored_total=10, scored_above_threshold=6, errors="")
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT * FROM runs").fetchall()
    conn.close()
    assert len(rows) == 1


def _content_hash(job: Job) -> str:
    import hashlib
    raw = f"{job.company.lower().strip()}{job.title.lower().strip()}{job.posted_date or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()
