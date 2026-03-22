import pytest
from unittest.mock import patch, MagicMock
from src.sources.ats import fetch_greenhouse, fetch_lever, fetch_ashby


def _mock_get(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


def test_fetch_greenhouse(mocker):
    mocker.patch("requests.get", return_value=_mock_get({
        "jobs": [{
            "title": "VP Marketing",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "location": {"name": "Remote"},
            "updated_at": "2026-03-20T10:00:00.000Z",
            "content": "Lead our marketing team.",
        }]
    }))
    jobs, errors = fetch_greenhouse(["acme"])
    assert len(jobs) == 1
    assert jobs[0].title == "VP Marketing"
    assert jobs[0].source == "greenhouse"
    assert errors == []


def test_fetch_lever(mocker):
    mocker.patch("requests.get", return_value=_mock_get([{
        "text": "CMO",
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "categories": {"location": "San Francisco, CA"},
        "createdAt": 1742000000000,
        "descriptionPlain": "Lead all marketing.",
    }]))
    jobs, errors = fetch_lever(["acme"])
    assert len(jobs) == 1
    assert jobs[0].source == "lever"


def test_fetch_ashby(mocker):
    mocker.patch("requests.get", return_value=_mock_get({
        "jobPostings": [{
            "title": "Head of Marketing",
            "jobUrl": "https://jobs.ashbyhq.com/acme/xyz",
            "isRemote": True,
            "locationName": "Remote",
            "updatedAt": "2026-03-21",
            "descriptionHtml": "<p>Lead marketing.</p>",
        }]
    }))
    jobs, errors = fetch_ashby(["acme"])
    assert len(jobs) == 1
    assert jobs[0].remote is True
    assert jobs[0].source == "ashby"


def test_source_error_is_captured(mocker):
    mocker.patch("requests.get", side_effect=Exception("Timeout"))
    jobs, errors = fetch_greenhouse(["nonexistent-company"])
    assert jobs == []
    assert len(errors) == 1
