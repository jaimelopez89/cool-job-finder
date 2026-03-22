import pytest
from unittest.mock import MagicMock, patch
from src.scorer import parse_score_response, compute_composite, score_job
from src.models import Job


def test_parse_valid_response():
    raw = """{
        "role_fit": 8,
        "company_fit": 7,
        "seniority_match": 9,
        "geography_fit": 6,
        "industry_fit": 8,
        "summary": "Strong fit for Product Marketing background.",
        "red_flags": "Office is Madrid-based.",
        "salary_estimate": "€130,000–€150,000"
    }"""
    result = parse_score_response(raw)
    assert result["role_fit"] == 8
    assert result["summary"] == "Strong fit for Product Marketing background."


def test_parse_response_with_markdown_fence():
    raw = """```json
    {"role_fit": 7, "company_fit": 8, "seniority_match": 7,
     "geography_fit": 9, "industry_fit": 8, "summary": "Good match.",
     "red_flags": "", "salary_estimate": ""}
    ```"""
    result = parse_score_response(raw)
    assert result["role_fit"] == 7


def test_parse_invalid_response_raises():
    with pytest.raises(ValueError, match="Could not parse"):
        parse_score_response("not json at all")


def test_compute_composite():
    dimensions = {
        "role_fit": 10,
        "company_fit": 10,
        "seniority_match": 10,
        "geography_fit": 10,
        "industry_fit": 10,
    }
    assert compute_composite(dimensions) == 100


def test_compute_composite_weighted():
    dimensions = {
        "role_fit": 10,      # 30%
        "company_fit": 0,    # 25%
        "seniority_match": 0,# 20%
        "geography_fit": 0,  # 15%
        "industry_fit": 0,   # 10%
    }
    # 10 * 0.30 * 10 = 30
    assert compute_composite(dimensions) == 30


def test_score_job_calls_claude():
    job = Job(
        title="VP Marketing", company="TechCo", url="https://techco.com/jobs/1",
        location="Remote", description="Lead marketing.", source="adzuna",
        salary_raw="€140,000", remote=True,
    )
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"role_fit":8,"company_fit":9,"seniority_match":8,"geography_fit":10,"industry_fit":9,"summary":"Great fit.","red_flags":"","salary_estimate":"€140,000"}')]
    mock_client.messages.create.return_value = mock_response

    result = score_job(job, client=mock_client, config={
        "salary_thresholds": {"general_minimum": 130000, "australia": 180000}
    })

    assert result["score"] == pytest.approx(87, abs=2)
    assert result["fit_summary"] == "Great fit."
    assert result["red_flags"] == ""
    assert "raw_dimensions" in result
    assert set(result["raw_dimensions"].keys()) == {"role_fit", "company_fit", "seniority_match", "geography_fit", "industry_fit"}
