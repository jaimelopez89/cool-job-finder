import json
import re
from typing import Any

import anthropic
import openai

from src.geo import assign_geo_bucket, enforce_salary_threshold
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
  Minimum salary: €130k for any role/location. Relocation to Spain/LATAM at ≥€130k.
- Geography scoring guide: fully remote roles = 9–10 (can be done from Helsinki);
  Finland/remote-friendly EU = 8–9; Spain/LATAM office = 6–8; other EU = 5–7; US-only office = 1–3.

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
        raise ValueError(f"Could not parse scorer response as JSON: {e}\nRaw: {raw[:300]}")


def compute_composite(dimensions: dict) -> int:
    missing = [k for k in _WEIGHTS if k not in dimensions]
    if missing:
        raise ValueError(f"Missing scoring dimensions: {missing}")
    score = sum(dimensions[k] * _WEIGHTS[k] for k in _WEIGHTS) * 10
    return round(score)


def _call_anthropic(client: anthropic.Anthropic, prompt: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_openai(client: openai.OpenAI, prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def score_job(job: Job, client: Any, config: dict) -> dict[str, Any]:
    prompt = _PROMPT_TEMPLATE.format(
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary_raw or "not mentioned",
        description=job.description[:4000],  # cap to avoid token overflow
    )

    try:
        if isinstance(client, openai.OpenAI):
            raw = _call_openai(client, prompt)
        else:
            raw = _call_anthropic(client, prompt)
    except Exception as e:
        raise RuntimeError(f"Scorer API call failed for '{job.title}' at '{job.company}': {e}") from e

    parsed = parse_score_response(raw)

    geo_bucket = assign_geo_bucket(job.location, remote=job.remote)
    adjusted_geo_fit, salary_flag = enforce_salary_threshold(
        geography_fit=parsed["geography_fit"],
        geo_bucket=geo_bucket,
        salary_str=parsed["salary_estimate"] or job.salary_raw,
        thresholds=config.get("salary_thresholds", {}),
    )
    parsed["geography_fit"] = adjusted_geo_fit

    red_flags = parsed.get("red_flags", "")
    if salary_flag and salary_flag not in red_flags:
        red_flags = f"{red_flags}; {salary_flag}".lstrip("; ")

    composite = compute_composite({k: parsed[k] for k in _WEIGHTS})

    return {
        "score": composite,
        "fit_summary": parsed.get("summary", ""),
        "red_flags": red_flags,
        "salary_estimate": parsed.get("salary_estimate", ""),
        "raw_dimensions": {k: parsed[k] for k in _WEIGHTS},
    }
