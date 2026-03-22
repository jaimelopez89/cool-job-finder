# Cool Job Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily job-finding pipeline that scrapes leading-edge company job postings, scores them against Jaime's profile using Claude AI, and displays results in a Streamlit dashboard organised by geography.

**Architecture:** A Python pipeline (`run.py`) fetches jobs from Adzuna API, public ATS APIs (Greenhouse/Lever/Ashby), and career page scrapers, deduplicates, scores each via Claude API, and writes to SQLite. A Streamlit app (`app.py`) reads from SQLite and displays results in five geo-tab leaderboards with applied/dismiss tracking.

**Tech Stack:** Python 3.11+, Streamlit, SQLite, `anthropic` SDK, `requests`, `beautifulsoup4`, `pyyaml`, `python-dotenv`, pytest

---

## File Map

```
cool-job-finder/
├── run.py                        # Pipeline orchestrator
├── app.py                        # Streamlit dashboard
├── config.yaml                   # Job titles, companies, thresholds
├── .env.example                  # API key template
├── .gitignore
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── models.py                 # Job dataclass (shared across sources)
│   ├── db.py                     # SQLite init, insert, query, update
│   ├── geo.py                    # Geo bucket assignment + salary enforcement
│   ├── scorer.py                 # Claude API scoring
│   └── sources/
│       ├── __init__.py
│       ├── adzuna.py             # Adzuna API client
│       ├── ats.py                # Greenhouse / Lever / Ashby clients
│       └── scraper.py            # Career page scraper
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_geo.py
│   ├── test_scorer.py
│   └── sources/
│       ├── __init__.py
│       ├── test_adzuna.py
│       ├── test_ats.py
│       └── test_scraper.py
└── docs/
    └── superpowers/
        ├── specs/2026-03-22-job-finder-design.md
        └── plans/2026-03-22-job-finder.md
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config.yaml`
- Create: `src/__init__.py`, `src/sources/__init__.py`, `tests/__init__.py`, `tests/sources/__init__.py`

- [ ] **Step 1: Initialise git repo**

```bash
cd /Users/Jaime/claude-personal/cool-job-finder
git init
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
data/
logs/
__pycache__/
*.pyc
.venv/
*.db
*.egg-info/
.DS_Store
```

- [ ] **Step 3: Create `requirements.txt`**

```
streamlit>=1.32.0
anthropic>=0.25.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 4: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 5: Create `.env.example`**

```
ADZUNA_APP_ID=your_app_id_here
ADZUNA_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

- [ ] **Step 6: Create `config.yaml`**

```yaml
job_titles:
  - "CMO"
  - "Chief Marketing Officer"
  - "Chief Product Officer"
  - "VP Marketing"
  - "VP Product Marketing"
  - "VP Growth"
  - "VP Demand Generation"
  - "VP Revenue Marketing"
  - "VP GTM Strategy"
  - "Chief Growth Officer"
  - "Director of Marketing"
  - "Senior Director of Marketing"
  - "Director of Product Marketing"
  - "Senior Director of Product Marketing"
  - "Director of Marketing Operations"
  - "Senior Director of Marketing Operations"
  - "Director of Revenue Marketing"
  - "Senior Director of Revenue Marketing"
  - "Director of Demand Generation"
  - "Senior Director of Demand Generation"
  - "Director of Growth Marketing"
  - "Senior Director of Growth Marketing"
  - "Director of GTM Strategy"
  - "Senior Director of GTM Strategy"
  - "Head of Marketing"
  - "Head of Product Marketing"
  - "Head of Demand Generation"
  - "Head of Growth"
  - "Director of Product Excellence"
  - "Director of Revenue Operations"
  - "VP of Product Management"
  - "Director of Product Management"
  - "Director of Product Strategy"
  - "Head of Product"
  - "Director of Field Marketing"
  - "VP of Developer Relations"
  - "Director of Developer Relations"
  - "Director of Portfolio Marketing"

adzuna:
  country_codes:
    - gb
    - fi
    - es
    - au
    - us
    - mx
    - br
  results_per_page: 50

target_companies:
  greenhouse:
    - databricks
    - confluent
    - elastic
    - gitlab
    - sentry
    - launchdarkly
    - scale-ai
    - cohere
    - cockroachdb
    - grafana
    - snyk
    - fivetran
    - starburst
    - imply
    - pinecone
  lever:
    - huggingface
    - mistral
    - airbyte
    - planetscale
    - jfrog
  ashby:
    - perplexity-ai
    - weaviate
    - qdrant
    - redpanda-data
    - neon
    - risingwave
  career_pages:
    - name: "Anthropic"
      url: "https://www.anthropic.com/careers"
    - name: "OpenAI"
      url: "https://openai.com/careers"
    - name: "Octopus Energy"
      url: "https://octopus.energy/careers/"
    - name: "Northvolt"
      url: "https://northvolt.com/careers/"
    - name: "Stability AI"
      url: "https://stability.ai/careers"

scoring:
  threshold: 60

salary_thresholds:
  general_minimum: 130000
  australia: 180000
```

- [ ] **Step 7: Create `__init__.py` files**

```bash
touch src/__init__.py src/sources/__init__.py tests/__init__.py tests/sources/__init__.py
```

- [ ] **Step 8: Create `data/` and `logs/` directories**

```bash
mkdir -p data logs
```

- [ ] **Step 9: Copy `.env.example` to `.env` and fill in your API keys**

```bash
cp .env.example .env
# Edit .env with real values
```

- [ ] **Step 10: Initial commit**

```bash
git add .
git commit -m "feat: project scaffold, config, and requirements"
```

---

## Task 2: Data Model

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: `FAILED` — `ModuleNotFoundError: No module named 'src.models'`

- [ ] **Step 3: Implement `src/models.py`**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Job:
    title: str
    company: str
    url: str
    location: str
    description: str
    source: str  # adzuna | greenhouse | lever | ashby | scraper
    salary_raw: Optional[str] = None
    remote: bool = False
    posted_date: Optional[date] = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: Job dataclass model"
```

---

## Task 3: Database Layer

**Files:**
- Create: `src/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

`tests/test_db.py`:
```python
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
    """Helper matching the hash logic in db.py."""
    import hashlib
    raw = f"{job.company.lower().strip()}{job.title.lower().strip()}{job.posted_date or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```
Expected: `FAILED` — `ModuleNotFoundError: No module named 'src.db'`

- [ ] **Step 3: Implement `src/db.py`**

```python
import hashlib
import sqlite3
from datetime import datetime
from typing import Any, Optional

from src.models import Job


def _content_hash(job: Job) -> str:
    raw = f"{job.company.lower().strip()}{job.title.lower().strip()}{job.posted_date or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            posted_date DATE,
            source TEXT NOT NULL,
            description TEXT,
            score INTEGER,
            fit_summary TEXT,
            red_flags TEXT,
            salary_estimate TEXT,
            geo_bucket TEXT,
            applied BOOLEAN DEFAULT 0,
            dismissed BOOLEAN DEFAULT 0,
            seen BOOLEAN DEFAULT 0,
            content_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            jobs_fetched INTEGER,
            new_jobs INTEGER,
            scored_total INTEGER,
            scored_above_threshold INTEGER,
            errors TEXT
        );
    """)
    conn.commit()
    conn.close()


def is_duplicate(db_path: str, url: str, content_hash: str) -> bool:
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT id FROM jobs WHERE url = ? OR content_hash = ?",
        (url, content_hash),
    ).fetchone()
    conn.close()
    return row is not None


def insert_job(
    db_path: str,
    job: Job,
    score: int,
    fit_summary: str,
    red_flags: str,
    salary_estimate: str,
    geo_bucket: str,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT OR IGNORE INTO jobs
           (title, company, url, posted_date, source, description, score,
            fit_summary, red_flags, salary_estimate, geo_bucket, content_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job.title, job.company, job.url, job.posted_date, job.source,
            job.description, score, fit_summary, red_flags, salary_estimate,
            geo_bucket, _content_hash(job),
        ),
    )
    conn.commit()
    conn.close()


def get_jobs(db_path: str, geo_bucket: Optional[str] = None, min_score: int = 0) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM jobs WHERE score >= ?"
    params: list[Any] = [min_score]
    if geo_bucket:
        query += " AND geo_bucket = ?"
        params.append(geo_bucket)
    query += " ORDER BY score DESC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def update_job_field(db_path: str, job_id: int, field: str, value: Any) -> None:
    allowed = {"applied", "dismissed", "seen"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not updatable. Allowed: {allowed}")
    conn = sqlite3.connect(db_path)
    conn.execute(f"UPDATE jobs SET {field} = ? WHERE id = ?", (value, job_id))
    conn.commit()
    conn.close()


def insert_run(
    db_path: str,
    jobs_fetched: int,
    new_jobs: int,
    scored_total: int,
    scored_above_threshold: int,
    errors: str,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO runs (jobs_fetched, new_jobs, scored_total, scored_above_threshold, errors)
           VALUES (?, ?, ?, ?, ?)""",
        (jobs_fetched, new_jobs, scored_total, scored_above_threshold, errors),
    )
    conn.commit()
    conn.close()


def get_last_run(db_path: str) -> Optional[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM runs ORDER BY run_date DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: SQLite database layer with deduplication"
```

---

## Task 4: Geo Module

**Files:**
- Create: `src/geo.py`
- Create: `tests/test_geo.py`

- [ ] **Step 1: Write failing tests**

`tests/test_geo.py`:
```python
from src.geo import assign_geo_bucket, enforce_salary_threshold


def test_remote_bucket():
    assert assign_geo_bucket("Remote", remote=True) == "remote"


def test_remote_flag_wins():
    assert assign_geo_bucket("San Francisco, CA", remote=True) == "remote"


def test_finland_bucket():
    assert assign_geo_bucket("Helsinki, Finland") == "finland"


def test_espoo_is_finland():
    assert assign_geo_bucket("Espoo, Finland") == "finland"


def test_spain_bucket():
    assert assign_geo_bucket("Madrid, Spain") == "spain_latam"


def test_barcelona_is_spain():
    assert assign_geo_bucket("Barcelona") == "spain_latam"


def test_mexico_is_latam():
    assert assign_geo_bucket("Mexico City, Mexico") == "spain_latam"


def test_brazil_is_latam():
    assert assign_geo_bucket("São Paulo, Brazil") == "spain_latam"


def test_australia_bucket():
    assert assign_geo_bucket("Sydney, Australia") == "australia"


def test_melbourne_is_australia():
    assert assign_geo_bucket("Melbourne") == "australia"


def test_other_bucket():
    assert assign_geo_bucket("New York, NY") == "other"


def test_salary_below_general_minimum_caps_geography_fit():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str="€100,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 2
    assert "below" in flags.lower()


def test_salary_below_australia_minimum():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="australia", salary_str="€150,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 2
    assert "below" in flags.lower()


def test_salary_above_threshold_unchanged():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str="€140,000", thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 8
    assert flags == ""


def test_salary_unlisted_adds_flag_no_penalty():
    score, flags = enforce_salary_threshold(
        geography_fit=8, geo_bucket="remote", salary_str=None, thresholds={"general_minimum": 130000, "australia": 180000}
    )
    assert score == 8
    assert "confirm" in flags.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_geo.py -v
```
Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/geo.py`**

```python
import re
from typing import Optional


_FINLAND_KEYWORDS = {"finland", "helsinki", "espoo", "tampere", "turku", "vantaa", "oulu"}
_SPAIN_KEYWORDS = {"spain", "españa", "madrid", "barcelona", "valencia", "seville", "bilbao"}
_LATAM_KEYWORDS = {"mexico", "brasil", "brazil", "colombia", "argentina", "chile", "peru",
                   "bogotá", "bogota", "lima", "santiago", "buenos aires", "são paulo",
                   "sao paulo", "mexico city"}
_AUSTRALIA_KEYWORDS = {"australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra"}
_REMOTE_KEYWORDS = {"remote", "anywhere", "distributed", "fully remote"}


def assign_geo_bucket(location: str, remote: bool = False) -> str:
    if remote:
        return "remote"

    loc = location.lower()

    if any(kw in loc for kw in _REMOTE_KEYWORDS):
        return "remote"
    if any(kw in loc for kw in _FINLAND_KEYWORDS):
        return "finland"
    if any(kw in loc for kw in _AUSTRALIA_KEYWORDS):
        return "australia"
    if any(kw in loc for kw in _SPAIN_KEYWORDS | _LATAM_KEYWORDS):
        return "spain_latam"
    return "other"


def _parse_salary(salary_str: str) -> Optional[float]:
    """Extract the lower-bound salary value from a string like '€130,000–€160,000'."""
    digits = re.findall(r"[\d,]+", salary_str.replace(".", ",").replace(" ", ""))
    if not digits:
        return None
    # Take the first number found (lower bound)
    try:
        return float(digits[0].replace(",", ""))
    except ValueError:
        return None


def enforce_salary_threshold(
    geography_fit: int,
    geo_bucket: str,
    salary_str: Optional[str],
    thresholds: dict,
) -> tuple[int, str]:
    """
    Returns (adjusted_geography_fit, red_flag_message).
    Caps geography_fit to 2 if salary is below threshold.
    Adds a warning flag if salary is not listed.
    """
    general_min = thresholds.get("general_minimum", 130000)
    australia_min = thresholds.get("australia", 180000)

    if salary_str is None:
        return geography_fit, "Salary not listed — confirm meets €130k minimum before applying."

    salary = _parse_salary(salary_str)
    if salary is None:
        return geography_fit, "Salary format unrecognised — confirm meets threshold before applying."

    threshold = australia_min if geo_bucket == "australia" else general_min
    if salary < threshold:
        return 2, f"Salary ({salary_str}) is below the €{threshold:,.0f} threshold for {geo_bucket}."

    return geography_fit, ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_geo.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/geo.py tests/test_geo.py
git commit -m "feat: geo bucket assignment and salary threshold enforcement"
```

---

## Task 5: Scorer Module

**Files:**
- Create: `src/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_scorer.py`:
```python
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


def test_score_job_calls_claude(mocker):
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scorer.py -v
```
Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/scorer.py`**

```python
import json
import re
from typing import Any

import anthropic

from src.geo import enforce_salary_threshold
from src.models import Job

_WEIGHTS = {
    "role_fit": 0.30,
    "company_fit": 0.25,
    "seniority_match": 0.20,
    "geography_fit": 0.15,
    "industry_fit": 0.10,
}

_PROMPT_TEMPLATE = """You are evaluating a job posting for a specific candidate. Return ONLY valid JSON matching the schema below. No prose outside the JSON block.

Candidate profile:
- Senior Product & Marketing leader, 12+ years B2B SaaS
- Target roles: CMO, Chief Product Officer, VP Marketing, VP Product Marketing, VP Growth, VP Demand Generation, Director/Senior Director of Marketing, Director/Senior Director of Product Marketing, Director/Senior Director of Marketing Operations, Head of Marketing, Head of Product, Director of Revenue Operations, and similar Director+ / VP / C-suite roles
- Preferred industries: AI/ML, real-time data/streaming, developer tools, cloud infrastructure, SaaS, energy tech
- Target companies: Series B–D, leading-edge tech, strong brand recognition in tech circles
- Location: Helsinki, Finland. Prefers fully remote. Open to southern Finland office.
  Minimum salary: €130k for any role/location. Relocation to Spain/LATAM at ≥€130k, Australia at ≥€180k.

Job posting:
Title: {title}
Company: {company}
Location: {location}
Salary (if mentioned): {salary}
Description:
{description}

Score each dimension 1–10. Return JSON only:
{{
  "role_fit": <int>,
  "company_fit": <int>,
  "seniority_match": <int>,
  "geography_fit": <int>,
  "industry_fit": <int>,
  "summary": "<one paragraph why this fits or doesn't fit the candidate>",
  "red_flags": "<comma-separated concerns, or empty string>",
  "salary_estimate": "<salary if mentioned, else empty string>"
}}"""


def parse_score_response(raw: str) -> dict:
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse Claude response as JSON: {e}\nRaw: {raw[:300]}")


def compute_composite(dimensions: dict) -> int:
    score = sum(dimensions[k] * _WEIGHTS[k] for k in _WEIGHTS) * 10
    return round(score)


def score_job(job: Job, client: anthropic.Anthropic, config: dict) -> dict[str, Any]:
    prompt = _PROMPT_TEMPLATE.format(
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary_raw or "not mentioned",
        description=job.description[:4000],  # cap to avoid token overflow
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    parsed = parse_score_response(response.content[0].text)

    # Apply salary threshold enforcement to geography_fit
    adjusted_geo_fit, salary_flag = enforce_salary_threshold(
        geography_fit=parsed["geography_fit"],
        geo_bucket="remote",  # conservative default; pipeline overrides with real bucket
        salary_str=parsed["salary_estimate"] or job.salary_raw,
        thresholds=config.get("salary_thresholds", {}),
    )
    parsed["geography_fit"] = adjusted_geo_fit

    red_flags = parsed.get("red_flags", "")
    if salary_flag:
        red_flags = f"{red_flags}; {salary_flag}".lstrip("; ")

    composite = compute_composite({k: parsed[k] for k in _WEIGHTS})

    return {
        "score": composite,
        "fit_summary": parsed.get("summary", ""),
        "red_flags": red_flags,
        "salary_estimate": parsed.get("salary_estimate", ""),
        "raw_dimensions": {k: parsed[k] for k in _WEIGHTS},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scorer.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/scorer.py tests/test_scorer.py
git commit -m "feat: Claude API scorer with weighted composite scoring"
```

---

## Task 6: Adzuna Source

**Files:**
- Create: `src/sources/adzuna.py`
- Create: `tests/sources/test_adzuna.py`

- [ ] **Step 1: Write failing tests**

`tests/sources/test_adzuna.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/sources/test_adzuna.py -v
```
Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/sources/adzuna.py`**

```python
import re
from datetime import date, datetime
from typing import Optional

import requests

from src.models import Job

_ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
_REMOTE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)


def build_search_queries(
    titles: list[str],
    country_codes: list[str],
    titles_per_query: int = 10,
) -> list[dict]:
    """Group job titles into OR-combined queries to stay within API call budget."""
    queries = []
    for i in range(0, len(titles), titles_per_query):
        batch = titles[i : i + titles_per_query]
        what = " OR ".join(f'"{t}"' for t in batch)
        for country in country_codes:
            queries.append({"country": country, "what": what})
    return queries


def normalize_adzuna_job(raw: dict) -> Job:
    title = raw.get("title", "")
    company = raw.get("company", {}).get("display_name", "Unknown")
    url = raw.get("redirect_url", "")
    location = raw.get("location", {}).get("display_name", "")
    description = raw.get("description", "")

    created_str = raw.get("created", "")
    posted_date: Optional[date] = None
    if created_str:
        try:
            posted_date = datetime.fromisoformat(created_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    salary_raw: Optional[str] = None
    if salary_min:
        salary_raw = f"€{salary_min:,.0f}" + (f"–€{salary_max:,.0f}" if salary_max else "")

    remote = bool(_REMOTE_PATTERN.search(location)) or bool(_REMOTE_PATTERN.search(title))

    return Job(
        title=title,
        company=company,
        url=url,
        location=location,
        description=description,
        source="adzuna",
        salary_raw=salary_raw,
        remote=remote,
        posted_date=posted_date,
    )


def fetch_adzuna_jobs(
    app_id: str,
    api_key: str,
    titles: list[str],
    country_codes: list[str],
    results_per_page: int = 50,
) -> tuple[list[Job], list[str]]:
    jobs: list[Job] = []
    errors: list[str] = []
    queries = build_search_queries(titles, country_codes)

    for q in queries:
        country = q["country"]
        url = f"{_ADZUNA_BASE}/{country}/search/1"
        try:
            resp = requests.get(
                url,
                params={
                    "app_id": app_id,
                    "app_key": api_key,
                    "what": q["what"],
                    "results_per_page": results_per_page,
                    "content-type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            for result in resp.json().get("results", []):
                jobs.append(normalize_adzuna_job(result))
        except Exception as e:
            errors.append(f"Adzuna [{country}]: {e}")

    return jobs, errors
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/sources/test_adzuna.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sources/adzuna.py tests/sources/test_adzuna.py
git commit -m "feat: Adzuna API source"
```

---

## Task 7: ATS Source (Greenhouse / Lever / Ashby)

**Files:**
- Create: `src/sources/ats.py`
- Create: `tests/sources/test_ats.py`

- [ ] **Step 1: Write failing tests**

`tests/sources/test_ats.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from src.sources.ats import fetch_greenhouse, fetch_lever, fetch_ashby, normalize_ats_job


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/sources/test_ats.py -v
```
Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/sources/ats.py`**

```python
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
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:26], fmt[:len(s)]).date()
        except ValueError:
            continue
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


def normalize_ats_job(raw: dict, source: str) -> Job:
    """Convenience wrapper — not used internally but useful for callers."""
    raise NotImplementedError("Use fetch_greenhouse / fetch_lever / fetch_ashby directly.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/sources/test_ats.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sources/ats.py tests/sources/test_ats.py
git commit -m "feat: Greenhouse, Lever, and Ashby ATS sources"
```

---

## Task 8: Career Page Scraper

**Files:**
- Create: `src/sources/scraper.py`
- Create: `tests/sources/test_scraper.py`

- [ ] **Step 1: Write failing tests**

`tests/sources/test_scraper.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/sources/test_scraper.py -v
```
Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/sources/scraper.py`**

```python
import re
from typing import Optional
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
        # Must be on the same domain and deeper than the careers path
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
            location_hint = text  # best we can do without fetching each job page
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/sources/test_scraper.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/sources/scraper.py tests/sources/test_scraper.py
git commit -m "feat: career page scraper source"
```

---

## Task 9: Pipeline Runner

**Files:**
- Create: `run.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

`tests/test_pipeline.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pipeline.py -v
```
Expected: `FAILED` — `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 3: Implement `run.py`**

```python
#!/usr/bin/env python3
"""Daily job-finding pipeline."""

import hashlib
import os
import sys
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

from src.db import init_db, insert_job, insert_run, is_duplicate
from src.geo import assign_geo_bucket, enforce_salary_threshold
from src.models import Job
from src.scorer import score_job
from src.sources.adzuna import fetch_adzuna_jobs
from src.sources.ats import fetch_ashby, fetch_greenhouse, fetch_lever
from src.sources.scraper import scrape_career_page

load_dotenv()

DB_PATH = str(Path(__file__).parent / "data" / "jobs.db")
CONFIG_PATH = str(Path(__file__).parent / "config.yaml")


def _content_hash(job: Job) -> str:
    raw = f"{job.company.lower().strip()}{job.title.lower().strip()}{job.posted_date or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def deduplicate_jobs(jobs: list[Job]) -> list[Job]:
    """Remove within-batch duplicates before hitting the DB."""
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    result = []
    for job in jobs:
        h = _content_hash(job)
        if job.url in seen_urls or h in seen_hashes:
            continue
        seen_urls.add(job.url)
        seen_hashes.add(h)
        result.append(job)
    return result


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def run_pipeline() -> None:
    config = load_config()
    init_db(DB_PATH)

    all_jobs: list[Job] = []
    all_errors: list[str] = []

    # 1. Adzuna
    print("Fetching from Adzuna...")
    adzuna_jobs, errs = fetch_adzuna_jobs(
        app_id=os.environ["ADZUNA_APP_ID"],
        api_key=os.environ["ADZUNA_API_KEY"],
        titles=config["job_titles"],
        country_codes=config["adzuna"]["country_codes"],
        results_per_page=config["adzuna"].get("results_per_page", 50),
    )
    all_jobs.extend(adzuna_jobs)
    all_errors.extend(errs)
    print(f"  Adzuna: {len(adzuna_jobs)} jobs, {len(errs)} errors")

    # 2. ATS APIs
    companies = config.get("target_companies", {})
    print("Fetching from Greenhouse...")
    gh_jobs, errs = fetch_greenhouse(companies.get("greenhouse", []))
    all_jobs.extend(gh_jobs)
    all_errors.extend(errs)

    print("Fetching from Lever...")
    lv_jobs, errs = fetch_lever(companies.get("lever", []))
    all_jobs.extend(lv_jobs)
    all_errors.extend(errs)

    print("Fetching from Ashby...")
    ab_jobs, errs = fetch_ashby(companies.get("ashby", []))
    all_jobs.extend(ab_jobs)
    all_errors.extend(errs)

    # 3. Career page scrapers
    print("Fetching from career pages...")
    for entry in companies.get("career_pages", []):
        page_jobs, errs = scrape_career_page(
            name=entry["name"],
            careers_url=entry["url"],
            target_titles=config["job_titles"],
        )
        all_jobs.extend(page_jobs)
        all_errors.extend(errs)

    jobs_fetched = len(all_jobs)
    print(f"Total fetched: {jobs_fetched} jobs")

    # 4. Deduplicate within batch
    all_jobs = deduplicate_jobs(all_jobs)

    # 5. Filter against DB
    new_jobs = [
        j for j in all_jobs
        if not is_duplicate(DB_PATH, url=j.url, content_hash=_content_hash(j))
    ]
    print(f"New jobs (not seen before): {len(new_jobs)}")

    # 6. Score and insert
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    scored_total = 0
    scored_above_threshold = 0
    threshold = config["scoring"]["threshold"]

    for job in new_jobs:
        try:
            geo_bucket = assign_geo_bucket(job.location, remote=job.remote)
            result = score_job(job, client=client, config=config)

            # Re-enforce salary threshold with real geo_bucket
            adj_geo_fit, salary_flag = enforce_salary_threshold(
                geography_fit=result["raw_dimensions"]["geography_fit"],
                geo_bucket=geo_bucket,
                salary_str=result["salary_estimate"] or job.salary_raw,
                thresholds=config.get("salary_thresholds", {}),
            )
            if salary_flag and salary_flag not in result["red_flags"]:
                result["red_flags"] = f"{result['red_flags']}; {salary_flag}".lstrip("; ")

            insert_job(
                DB_PATH,
                job,
                score=result["score"],
                fit_summary=result["fit_summary"],
                red_flags=result["red_flags"],
                salary_estimate=result["salary_estimate"],
                geo_bucket=geo_bucket,
            )
            scored_total += 1
            if result["score"] >= threshold:
                scored_above_threshold += 1
        except Exception as e:
            all_errors.append(f"Scoring [{job.company} - {job.title}]: {e}")

    # 7. Write run summary
    insert_run(
        DB_PATH,
        jobs_fetched=jobs_fetched,
        new_jobs=len(new_jobs),
        scored_total=scored_total,
        scored_above_threshold=scored_above_threshold,
        errors="\n".join(all_errors),
    )

    print(f"\nRun complete: {len(new_jobs)} new jobs found, {scored_above_threshold} scored ≥ {threshold}")
    if all_errors:
        print(f"Errors ({len(all_errors)}):")
        for e in all_errors:
            print(f"  {e}")


if __name__ == "__main__":
    run_pipeline()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_pipeline.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_pipeline.py
git commit -m "feat: daily pipeline runner with deduplication and scoring"
```

---

## Task 10: Streamlit Dashboard

**Files:**
- Create: `app.py`

No unit tests for the dashboard — Streamlit UI is tested manually.

- [ ] **Step 1: Implement `app.py`**

```python
"""Cool Job Finder — Streamlit Dashboard."""

import subprocess
import sys
from pathlib import Path

import streamlit as st
import yaml

from src.db import get_jobs, get_last_run, init_db, update_job_field

DB_PATH = str(Path(__file__).parent / "data" / "jobs.db")
CONFIG_PATH = str(Path(__file__).parent / "config.yaml")

st.set_page_config(page_title="Cool Job Finder", page_icon="🎯", layout="wide")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def score_badge(score: int) -> str:
    if score >= 80:
        return f"🟢 {score}"
    if score >= 65:
        return f"🟡 {score}"
    return f"🔴 {score}"


def render_job_row(job: dict, db_path: str) -> None:
    with st.expander(f"{score_badge(job['score'])}  **{job['title']}** — {job['company']}  |  {job['posted_date'] or 'Date unknown'}"):
        update_job_field(db_path, job["id"], "seen", True)

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Fit summary:** {job['fit_summary']}")
            if job["red_flags"]:
                st.warning(f"⚠️ {job['red_flags']}")
            if job["salary_estimate"]:
                st.markdown(f"**Salary:** {job['salary_estimate']}")
            st.markdown(f"[View job posting →]({job['url']})")
        with col2:
            applied = st.checkbox("Applied", value=bool(job["applied"]), key=f"applied_{job['id']}")
            if applied != bool(job["applied"]):
                update_job_field(db_path, job["id"], "applied", applied)

            dismissed = st.checkbox("Dismiss", value=bool(job["dismissed"]), key=f"dismissed_{job['id']}")
            if dismissed != bool(job["dismissed"]):
                update_job_field(db_path, job["id"], "dismissed", dismissed)


def render_tab(geo_bucket: str, label: str, db_path: str, min_score: int, hide_dismissed: bool) -> None:
    jobs = get_jobs(db_path, geo_bucket=geo_bucket, min_score=min_score)
    if hide_dismissed:
        jobs = [j for j in jobs if not j["dismissed"]]

    st.caption(f"{len(jobs)} roles matching current filters")

    if not jobs:
        st.info("No jobs found for this region with current filters.")
        return

    for job in jobs:
        render_job_row(job, db_path)


def main() -> None:
    init_db(DB_PATH)

    # Sidebar
    with st.sidebar:
        st.title("🎯 Cool Job Finder")
        st.divider()

        last_run = get_last_run(DB_PATH)
        if last_run:
            st.metric("Last run", str(last_run["run_date"])[:16])
            st.metric("New jobs (last run)", last_run["new_jobs"])
            st.metric("Scored ≥ threshold", last_run["scored_above_threshold"])

        all_jobs = get_jobs(DB_PATH, min_score=0)
        applied_count = sum(1 for j in all_jobs if j["applied"])
        st.metric("Total tracked", len(all_jobs))
        st.metric("Applied", applied_count)

        st.divider()
        st.subheader("Filters")
        min_score = st.slider("Minimum score", 0, 100, 60)
        hide_dismissed = st.toggle("Hide dismissed", value=True)

        st.divider()
        if st.button("▶ Run pipeline now"):
            with st.spinner("Running pipeline..."):
                result = subprocess.run(
                    [sys.executable, "run.py"],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent),
                )
            if result.returncode == 0:
                lines = [l for l in result.stdout.strip().splitlines() if l]
                st.success(lines[-1] if lines else "Done.")
            else:
                st.error(f"Pipeline failed:\n{result.stderr[:500]}")
            st.rerun()

    # Main content
    st.title("Job Leaderboard")

    tab_remote, tab_finland, tab_spain, tab_australia, tab_other = st.tabs([
        "🌍 Remote", "🇫🇮 Finland", "🇪🇸 Spain / LATAM", "🇦🇺 Australia", "📍 Other"
    ])

    with tab_remote:
        render_tab("remote", "Remote", DB_PATH, min_score, hide_dismissed)

    with tab_finland:
        render_tab("finland", "Finland", DB_PATH, min_score, hide_dismissed)

    with tab_spain:
        render_tab("spain_latam", "Spain / LATAM", DB_PATH, min_score, hide_dismissed)

    with tab_australia:
        render_tab("australia", "Australia", DB_PATH, min_score, hide_dismissed)

    with tab_other:
        # Higher threshold for "Other" tab to reduce noise
        other_min = max(min_score, 75)
        st.caption(f"Minimum score for 'Other' is {other_min} to reduce noise.")
        render_tab("other", "Other", DB_PATH, other_min, hide_dismissed)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the dashboard locally to verify it loads**

```bash
streamlit run app.py
```
Expected: dashboard opens at `http://localhost:8501` with five tabs. "No jobs found" shown initially (empty DB is fine).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit dashboard with 5 geo tabs and pipeline trigger"
```

---

## Task 11: Full Pipeline Smoke Test

Manual integration test — requires real API keys in `.env`.

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```
Expected: all tests `PASSED`

- [ ] **Step 2: Run the pipeline once manually**

```bash
python run.py
```
Expected output:
```
Fetching from Adzuna...
  Adzuna: N jobs, 0 errors
Fetching from Greenhouse...
...
Total fetched: N jobs
New jobs (not seen before): N
Run complete: N new jobs found, M scored ≥ 60
```

- [ ] **Step 3: Open the dashboard and verify results appear**

```bash
streamlit run app.py
```
Check:
- Jobs appear in the correct geo tabs
- Scores and summaries are populated
- Applied toggle and Dismiss button work
- Sidebar stats (last run, new jobs, applied count) are correct
- "Run pipeline now" button triggers another run and refreshes

- [ ] **Step 4: Set up daily cron job**

```bash
crontab -e
```
Add:
```
0 7 * * * cd /Users/Jaime/claude-personal/cool-job-finder && /Users/Jaime/claude-personal/cool-job-finder/.venv/bin/python run.py >> logs/run.log 2>&1
```

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: cool-job-finder v1 complete"
```

---

## Out of Scope (v1)

- LinkedIn native scraping
- Email digest notifications
- Multi-user support
- Streamlit Community Cloud deployment (run `streamlit run app.py` locally until ready to deploy)
