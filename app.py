"""Cool Job Finder — Streamlit Dashboard."""

import subprocess
import sys
from pathlib import Path

import streamlit as st

from src.db import get_jobs, get_last_run, init_db, update_job_field

DB_PATH = str(Path(__file__).parent / "data" / "jobs.db")
CONFIG_PATH = str(Path(__file__).parent / "config.yaml")

st.set_page_config(page_title="Cool Job Finder", page_icon="🎯", layout="wide")


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
