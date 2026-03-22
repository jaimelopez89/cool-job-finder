from dataclasses import dataclass
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
