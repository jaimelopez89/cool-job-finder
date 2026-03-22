#!/usr/bin/env python3
"""Daily job-finding pipeline."""

import os
import sys
from pathlib import Path

import anthropic
import openai
import yaml
from dotenv import load_dotenv

from src.db import _content_hash, init_db, insert_job, insert_run, is_duplicate
from src.geo import assign_geo_bucket
from src.models import Job
from src.scorer import score_job
from src.sources.adzuna import fetch_adzuna_jobs
from src.sources.ats import fetch_ashby, fetch_greenhouse, fetch_lever
from src.sources.scraper import scrape_career_page

load_dotenv()

DB_PATH = str(Path(__file__).parent / "data" / "jobs.db")
CONFIG_PATH = str(Path(__file__).parent / "config.yaml")


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


def prefilter_by_title(jobs: list[Job], target_titles: list[str]) -> list[Job]:
    """Keep only jobs whose title matches at least one target role keyword.

    ATS APIs return ALL open roles at a company (engineers, designers, etc.).
    This filter keeps only Director+/VP/C-suite marketing and product roles
    before spending Claude API budget on scoring.

    Strategy: match on *function* keywords (marketing, growth, revenue...) rather
    than level keywords (director, senior...) to avoid matching engineering directors.
    C-suite acronyms (cmo, cpo) are matched directly.
    """
    # Function keywords that identify the right roles — extracted from target title list
    function_keywords: set[str] = {
        "marketing", "growth", "revenue", "demand", "generation",
        "gtm", "go-to-market", "brand", "content", "communications",
        "excellence", "developer relations", "devrel", "portfolio",
        "product management", "product strategy", "product marketing",
        "field marketing", "market",
    }
    # C-suite short titles matched as whole words
    csuite: set[str] = {"cmo", "cpo", "cgo", "cto", "cro"}

    matched = []
    for job in jobs:
        title_lower = job.title.lower()
        if any(kw in title_lower for kw in function_keywords):
            matched.append(job)
        elif any(title_lower == kw or f" {kw}" in title_lower or title_lower.startswith(kw) for kw in csuite):
            matched.append(job)
    return matched


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

    # 5. Pre-filter by title relevance (keeps only marketing/product leadership roles)
    all_jobs = prefilter_by_title(all_jobs, config["job_titles"])
    print(f"After title filter: {len(all_jobs)} relevant jobs")

    # 6. Filter against DB (skip already-seen jobs)
    new_jobs = [
        j for j in all_jobs
        if not is_duplicate(DB_PATH, url=j.url, content_hash=_content_hash(j))
    ]
    print(f"New jobs (not seen before): {len(new_jobs)}")

    # Cap per-run scoring to avoid runaway API costs
    max_per_run = config.get("max_per_run", 75)
    if len(new_jobs) > max_per_run:
        print(f"Capping to {max_per_run} jobs this run (set max_per_run in config.yaml to change)")
        new_jobs = new_jobs[:max_per_run]

    # 7. Score and insert
    provider = config.get("scoring", {}).get("provider", "anthropic")
    if provider == "openai":
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        print("Scoring with OpenAI (gpt-4.1-nano)")
    else:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        print("Scoring with Anthropic (claude-haiku-4-5)")
    scored_total = 0
    scored_above_threshold = 0
    threshold = config["scoring"]["threshold"]
    total_to_score = len(new_jobs)

    for i, job in enumerate(new_jobs, 1):
        try:
            print(f"  Scoring {i}/{total_to_score}: {job.title} @ {job.company}...", end=" ", flush=True)
            geo_bucket = assign_geo_bucket(job.location, remote=job.remote)
            result = score_job(job, client=client, config=config)
            print(f"score={result['score']}")

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
            print(f"ERROR")
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
