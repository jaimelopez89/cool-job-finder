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
