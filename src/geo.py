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
    digits = re.findall(r"[\d,]+", salary_str.replace(".", ",").replace(" ", ""))
    if not digits:
        return None
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
