# Cool Job Finder — Design Spec
_Date: 2026-03-22_

## Overview

A daily job-finding app for Jaime López — a Director-level Product & Marketing leader based in Helsinki, Finland. The app scrapes and aggregates job postings from multiple sources, scores each for fit using Claude AI, and surfaces results in a local Streamlit dashboard organised by geography. Designed for **passive/opportunistic** use: high signal, low noise, weekly review cadence.

---

## User Profile

- **Target roles**: CMO, Chief Product Officer, VP Marketing, VP Product Marketing, VP Growth, VP Demand Generation, VP Revenue Marketing, VP GTM Strategy, Chief Growth Officer, Director/Senior Director of Marketing, Director/Senior Director of Product Marketing, Director/Senior Director of Marketing Operations, Director/Senior Director of Revenue Marketing, Director/Senior Director of Demand Generation, Director/Senior Director of Growth Marketing, Director/Senior Director of GTM Strategy, Head of Marketing, Head of Product Marketing, Head of Demand Generation, Head of Growth, Director of Product Excellence, Director of Revenue Operations, VP/Director of Product Management, Director of Product Strategy, Head of Product, Director of Field Marketing, VP/Director of Developer Relations, Director of Portfolio Marketing
- **Preferred industries**: AI/ML, real-time data/streaming, developer tools, cloud infrastructure, SaaS, energy tech
- **Leading-edge signals**: frontier technology, Series B–D funding, strong brand recognition in tech circles
- **Search mode**: Passive — quality over quantity, weekly review
- **Geography & salary thresholds**:
  - General minimum across all geos: ≥ €130,000
  - Fully remote: ≥ €130,000
  - Southern Finland / Helsinki office: ≥ €130,000
  - Spain / LATAM office: ≥ €130,000 (relocation considered at this level)
  - Australia office: ≥ €180,000

---

## Architecture

```
┌─────────────────────────────────────┐
│           Daily Runner              │
│           (run.py, cron)            │
│                                     │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ Adzuna   │  │ ATS APIs         │ │
│  │ API      │  │ (Greenhouse,     │ │
│  │          │  │  Lever, Ashby)   │ │
│  └──────────┘  └──────────────────┘ │
│  ┌──────────────────────────────┐   │
│  │ Career Page Scraper          │   │
│  │ (BeautifulSoup/requests)     │   │
│  └──────────────────────────────┘   │
│              │                      │
│              ▼                      │
│      Deduplication layer            │
│              │                      │
│              ▼                      │
│      Claude API Scorer              │
│              │                      │
│              ▼                      │
│          SQLite DB                  │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      Streamlit Dashboard            │
│   (tabs: Remote / Finland /         │
│    Spain+LATAM / Australia / Other) │
└─────────────────────────────────────┘
```

---

## Data Sources

### 1. Adzuna API
- Free tier: 250 calls/day
- Keyword search across all target job titles
- Geographic targets queried by Adzuna country code:
  - `gb` (UK, catches many international remote roles)
  - `fi` (Finland)
  - `es` (Spain)
  - `au` (Australia)
  - `us` (US remote roles)
  - Note: Adzuna has thin LATAM coverage — Mexico (`mx`) and Brazil (`br`) are available but sparse. For LATAM, career page scraping and ATS polling of known LATAM-active companies is the primary fallback.
- Catches aggregated postings from Indeed, Glassdoor, and thousands of other boards
- With ~10 country codes × title batches, stay within 250 calls/day by grouping title keywords into ≤3 OR-combined search queries per country

### 2. Public ATS APIs (no auth required)
- **Greenhouse**: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs`
- **Lever**: `https://api.lever.co/v0/postings/{company}`
- **Ashby**: `https://api.ashbyhq.com/posting-public/job-board/{company}`
- Polled for a curated list of ~100 leading-edge companies (AI, data, energy tech)

### 3. Career Page Scraper
- BeautifulSoup + requests
- For companies not using a standard ATS
- Targets `/careers` or `/jobs` pages of additional curated companies

### Deduplication
- **Primary key**: `url` (declared `UNIQUE` in schema) — sufficient for same-source deduplication
- **Secondary content hash**: `SHA256(company_normalised + title_normalised + posted_date)` stored as `content_hash` column — catches the same job appearing across multiple sources (e.g. Adzuna and the company's own Greenhouse board)
- Pipeline checks both: skip if URL already exists OR if content_hash already exists
- Already-seen jobs skipped entirely — only net-new postings are scored

---

## LLM Fit Scoring

Each new job is scored by Claude on five dimensions (1–10 each):

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Role fit | 30% | Title + responsibilities match target roles |
| Company fit | 25% | Leading-edge company in preferred vertical |
| Seniority match | 20% | Genuinely Director+ / VP / C-suite |
| Geography fit | 15% | Remote-friendly or office in valid location with salary threshold met |
| Industry fit | 10% | AI, real-time data, developer tools, energy, software |

**Composite score**: weighted average → 0–100

**Output per job** — Claude returns structured JSON:
```json
{
  "role_fit": 8,
  "company_fit": 7,
  "seniority_match": 9,
  "geography_fit": 6,
  "industry_fit": 8,
  "summary": "Strong fit for your Product Marketing background...",
  "red_flags": "Office is Madrid-based; salary not mentioned — threshold unconfirmed.",
  "salary_estimate": "€130,000–€150,000"
}
```

**Salary threshold enforcement** in `geo.py`:
- If salary is listed below €130k for any geo_bucket → `geography_fit` score capped at 2
- If geo_bucket is `australia` and salary is listed below €180k → `geography_fit` score capped at 2
- If salary is not mentioned → `geography_fit` is not penalised, but a red flag is added: "Salary not listed — confirm meets €130k minimum before applying"
- Jobs scoring below 60 are stored but hidden by default in the dashboard

**Prompt template skeleton** (`src/scorer.py`):
```
You are evaluating a job posting for a specific candidate. Return ONLY valid JSON matching the schema below.

Candidate profile:
- Senior Product & Marketing leader, 12+ years B2B SaaS
- Target roles: [list from config]
- Preferred industries: AI, real-time data, developer tools, SaaS, energy tech
- Target companies: Series B-D, leading-edge tech, strong brand
- Location: Helsinki, Finland. Prefers remote. Open to southern Finland office.
  Minimum salary: €130k for any role/location. Relocation to Spain/LATAM at ≥€130k, Australia at ≥€180k.

Job posting:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Score each dimension 1-10. Return JSON only, no prose outside the JSON block.
```

---

## Database Schema (SQLite)

### `jobs`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Job title |
| company | TEXT | Company name |
| url | TEXT UNIQUE | Source URL |
| posted_date | DATE | When posted |
| source | TEXT | adzuna / greenhouse / lever / ashby / scraper |
| description | TEXT | Raw job description |
| score | INTEGER | 0–100 composite fit score |
| fit_summary | TEXT | Claude's one-paragraph summary |
| red_flags | TEXT | Any concerns noted by Claude |
| salary_estimate | TEXT | Salary if mentioned |
| geo_bucket | TEXT | remote / finland / spain_latam / other |
| applied | BOOLEAN | Whether user has applied |
| dismissed | BOOLEAN | Whether user has dismissed |
| seen | BOOLEAN | Whether user has opened the detail view |
| content_hash | TEXT UNIQUE | SHA256(company_normalised + title_normalised + posted_date) for cross-source dedup |
| created_at | TIMESTAMP | When inserted into DB |

### `runs`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| run_date | TIMESTAMP | When the run executed |
| jobs_fetched | INTEGER | Total jobs retrieved from sources |
| new_jobs | INTEGER | Net new (not previously seen) |
| scored_total | INTEGER | Jobs for which Claude API was called successfully |
| scored_above_threshold | INTEGER | Jobs with composite score ≥ 60 |
| errors | TEXT | Any source errors encountered |

---

## Configuration (`config.yaml`)

```yaml
job_titles:
  - "CMO"
  - "Chief Marketing Officer"
  - "Chief Product Officer"
  - "VP Marketing"
  - "VP Product Marketing"
  # ... full list

target_companies:
  greenhouse:
    - confluent
    - databricks
    - elastic
    # ...
  lever:
    - anthropic
    - mistral
    # ...
  ashby:
    - ververica
    # ...
  career_pages:
    - name: "Example Corp"
      url: "https://example.com/careers"

scoring:
  threshold: 60

salary_thresholds:
  general_minimum: 130000
  australia: 180000

api_keys:
  adzuna_app_id: "${ADZUNA_APP_ID}"
  adzuna_api_key: "${ADZUNA_API_KEY}"
  anthropic_api_key: "${ANTHROPIC_API_KEY}"
```

---

## Streamlit Dashboard

### Layout
Five tabs, one per geo bucket:
- **Remote** — fully remote roles
- **Finland** — office in southern Finland / Helsinki
- **Spain / LATAM** — office roles, salary ≥ €130k
- **Australia** — office roles, salary ≥ €180k
- **Other** — any location not matching the above (shown only if score ≥ 75 to reduce noise)

### Per-tab features
- Jobs ranked by fit score (descending)
- Columns: Score | Title | Company | Posted | Salary | Summary (one line)
- Score threshold slider (default: 60)
- Filter by role category (CMO/VP, Director, Product, Marketing Ops…)
- Hide dismissed toggle
- Expandable row: full fit summary, red flags, direct link to posting
- **Applied** toggle — marks job as applied in DB
- **Dismiss** button — hides job from default view
- `seen` is set to `True` automatically when a row is expanded in the dashboard; used only for the "new this week" sidebar stat (unseen jobs posted in last 7 days)

### Sidebar
- Last run timestamp
- Stats: total jobs tracked, new this week, applied count
- "Run now" button — triggers `run.py` via `subprocess.Popen`, shows a spinner while running, displays final summary line ("X new jobs found, Y scored ≥ 60") when complete. Does not stream logs in the UI; full output is available in `logs/run.log`.

---

## Data Pipeline (`run.py`)

```
1. Load config.yaml and .env
2. Fetch from Adzuna API (all title keywords × geo targets)
3. Fetch from ATS APIs (Greenhouse, Lever, Ashby) for curated company list
4. Scrape career pages for remaining curated companies
5. Deduplicate against SQLite (skip known URLs)
6. For each new job:
   a. Call Claude API with job description + user profile context
   b. Parse structured scoring response
   c. Assign geo_bucket based on location + remote flag
7. Write all new scored jobs to SQLite
8. Write run summary to `runs` table
9. Print: "Run complete: X new jobs found, Y scored ≥ 60"
```

---

## Scheduler (macOS)

```bash
# crontab entry — runs daily at 7:00am
0 7 * * * cd /path/to/cool-job-finder && source .venv/bin/activate && python run.py >> logs/run.log 2>&1
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Dashboard | Streamlit |
| Database | SQLite (via `sqlite3` stdlib) |
| HTTP | `requests` |
| HTML parsing | `beautifulsoup4` |
| AI scoring | Anthropic Claude API (`anthropic` SDK) |
| Config | `pyyaml` + `python-dotenv` |
| Deployment (later) | Streamlit Community Cloud |

---

## Project Structure

```
cool-job-finder/
├── run.py                  # Daily pipeline runner
├── app.py                  # Streamlit dashboard
├── config.yaml             # Job titles, companies, thresholds
├── .env                    # API keys (gitignored)
├── data/
│   └── jobs.db             # SQLite database (gitignored)
├── logs/
│   └── run.log             # Pipeline logs (gitignored)
├── src/
│   ├── sources/
│   │   ├── adzuna.py       # Adzuna API client
│   │   ├── ats.py          # Greenhouse/Lever/Ashby clients
│   │   └── scraper.py      # Career page scraper
│   ├── scorer.py           # Claude API scoring logic
│   ├── db.py               # SQLite helpers
│   └── geo.py              # Geo bucket assignment logic
├── requirements.txt
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-22-job-finder-design.md
```

---

## Out of Scope (v1)

- LinkedIn native scraping (ToS risk; Adzuna aggregates most LinkedIn postings anyway)
- Email notifications
- Multi-user support
- Mobile-optimised UI
- Automatic application submission
