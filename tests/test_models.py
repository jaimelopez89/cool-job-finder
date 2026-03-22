from src.models import Job
from datetime import date

def test_job_defaults():
    job = Job(
        title="VP Marketing",
        company="Acme Corp",
        url="https://example.com/jobs/1",
        location="Remote",
        description="Lead our marketing team.",
        source="adzuna",
    )
    assert job.remote is False
    assert job.salary_raw is None
    assert job.posted_date is None

def test_job_with_all_fields():
    job = Job(
        title="CMO",
        company="TechCo",
        url="https://techco.com/jobs/cmo",
        location="Helsinki, Finland",
        description="Chief Marketing Officer role.",
        source="greenhouse",
        salary_raw="€140,000–€160,000",
        remote=False,
        posted_date=date(2026, 3, 22),
    )
    assert job.salary_raw == "€140,000–€160,000"
    assert job.posted_date == date(2026, 3, 22)
