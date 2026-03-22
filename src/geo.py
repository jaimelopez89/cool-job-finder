import re
from typing import Optional


_FINLAND_KEYWORDS = {"finland", "helsinki", "espoo", "tampere", "turku", "vantaa", "oulu"}
_SPAIN_KEYWORDS = {"spain", "españa", "madrid", "barcelona", "valencia", "seville", "bilbao"}
_LATAM_KEYWORDS = {"mexico", "brasil", "brazil", "colombia", "argentina", "chile", "peru",
                   "bogotá", "bogota", "lima", "santiago", "buenos aires", "são paulo",
                   "sao paulo", "mexico city"}
_REMOTE_KEYWORDS = {"remote", "anywhere", "distributed", "fully remote"}


def assign_geo_bucket(location: str, remote: bool = False) -> str:
    if remote:
        return "remote"

    loc = location.lower()

    if any(kw in loc for kw in _REMOTE_KEYWORDS):
        return "remote"
    if any(kw in loc for kw in _FINLAND_KEYWORDS):
        return "finland"
    if any(kw in loc for kw in _SPAIN_KEYWORDS | _LATAM_KEYWORDS):
        return "spain_latam"
    return "other"


def _parse_salary(salary_str: str) -> Optional[float]:
    """Extract the lower-bound salary value from strings like '€130,000–€160,000' or '€130.000'."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[€$£¥\s]", "", salary_str)
    # Find all number-like sequences (digits with optional separators)
    # Match patterns like: 130,000 or 130.000 or 130000 or 1.3M
    candidates = re.findall(r"[\d]+(?:[.,][\d]+)*", cleaned)
    if not candidates:
        return None
    # Take the first (lower bound) candidate
    raw = candidates[0]
    # Determine if period is thousands separator (e.g. 130.000) or decimal (e.g. 95.5)
    # Heuristic: if ends with exactly 3 digits after the last separator, treat as thousands
    if re.match(r"^\d{1,3}[.,]\d{3}$", raw):
        # Thousands separator format: remove it
        return float(raw.replace(",", "").replace(".", ""))
    elif "," in raw and re.search(r",\d{3}$", raw):
        # Comma as thousands separator: 130,000
        return float(raw.replace(",", ""))
    elif "." in raw and re.search(r"\.\d{3}$", raw):
        # Period as thousands separator: 130.000
        return float(raw.replace(".", ""))
    else:
        # Try direct conversion (handles 130000 or 95.5)
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None


def enforce_salary_threshold(
    geography_fit: int,
    geo_bucket: str,
    salary_str: Optional[str],
    thresholds: dict,
) -> tuple[int, str]:
    general_min = thresholds.get("general_minimum", 130000)

    if salary_str is None:
        return geography_fit, "Salary not listed — confirm meets €130k minimum before applying."

    salary = _parse_salary(salary_str)
    if salary is None:
        return geography_fit, "Salary format unrecognised — confirm meets threshold before applying."

    threshold = general_min
    if salary < threshold:
        return 2, f"Salary ({salary_str}) is below the €{threshold:,.0f} threshold for {geo_bucket}."

    return geography_fit, ""
