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

    # Apply salary threshold enforcement with conservative "remote" default
    # (pipeline will re-enforce with real geo_bucket)
    adjusted_geo_fit, salary_flag = enforce_salary_threshold(
        geography_fit=parsed["geography_fit"],
        geo_bucket="remote",
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
