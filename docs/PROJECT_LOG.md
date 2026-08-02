# F1 Analytics & GenAI Project — Build Journal

This log documents what was actually built each day, problems hit along the way, how they were solved, and why each decision was made. Kept as a personal reference and as proof of a real debugging process — not a polished "everything worked first try" narrative.

---

## Project Structure (as of end of Day 2)

```
F1-analytics/
├── .env                          # Kaggle API token (gitignored, never committed)
├── .env.example                  # Template showing required env vars (committed)
├── .gitignore
├── requirements.txt
├── data/
│   ├── raw/
│   │   ├── career_stats/
│   │   │   ├── F1_driver.csv         # Kaggle: kushagrajain19/f1-drivers-dataset-1950-2026
│   │   │   └── _manifest.json
│   │   └── race_history/
│   │       ├── circuits.csv
│   │       ├── constructors.csv
│   │       ├── constructor_results.csv
│   │       ├── constructor_standings.csv
│   │       ├── drivers.csv
│   │       ├── driver_standings.csv
│   │       ├── lap_times.csv
│   │       ├── pit_stops.csv
│   │       ├── qualifying.csv
│   │       ├── races.csv
│   │       ├── results.csv
│   │       ├── seasons.csv
│   │       ├── sprint_results.csv
│   │       ├── status.csv
│   │       └── _manifest.json        # Kaggle: rohanrao/formula-1-world-championship-1950-2020
│   └── processed/
│       └── race_history/
│           └── (14 cleaned .parquet files, one per raw CSV)
├── notebooks/
│   ├── 01_extraction_exploration.ipynb
│   └── 02_etl_cleaning.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py                 # centralized paths + dataset handles
│   ├── extract.py                # kagglehub download + copy + manifest logic
│   └── transform.py              # clean_nulls(), parse_lap_time()
├── sql/                           # (not yet started — Day 3)
├── genai/                         # (not yet started — Day 9)
├── dashboards/                    # (not yet started — Day 7/8)
├── tests/                         # (not yet started)
└── docs/
    └── PROJECT_LOG.md             # this file
```

---

## Key Architectural Decision: Two Datasets, Not One

**What happened:** The originally chosen Kaggle dataset (`kushagrajain19/f1-drivers-dataset-1950-2026`) turned out to be a **pre-aggregated driver career-summary table** — 876 rows, one row per driver, with stats like `Win_Rate` and `Podium_Rate` already calculated. It has no race-by-race grain at all.

**Why that was a problem:** the project's core goals — star schema fact tables, rolling averages, grid-position deltas, reliability rates per season — all require **race-by-race event data**, which this dataset doesn't have.

**Decision made:** rather than force-fit the project scope down to what one flat CSV could support, added a second dataset — the classic `rohanrao/formula-1-world-championship-1950-2020` — which provides the full relational structure (drivers, races, results, qualifying, pit_stops, lap_times, constructors, circuits, status).

**How they're used together going forward:**
- `F1_driver.csv` (career stats) → enrichment fields added onto the driver dimension table in the warehouse (Day 3/4).
- Classic dataset (14 tables) → the primary source for fact tables, SQL analytics, and feature engineering (Days 3–9).

**Why this is worth highlighting on a resume:** it's a real multi-source integration decision, not just "downloaded a CSV." Worth a line like: *"Identified a mismatch between initial dataset grain and project requirements mid-build, and integrated a second complementary dataset rather than compromising analytical scope."*

---

## Day 1 — Setup, Repo, Kaggle Extraction

### What was built
- Git repo initialized, full folder skeleton created (adapted for PowerShell/Windows).
- Python virtual environment (`venv`) set up, `requirements.txt` installed.
- `.gitignore` created to exclude secrets, data files, and environment folders.
- `.env` / `.env.example` set up for Kaggle authentication.
- `src/config.py` — centralizes all paths and dataset identifiers using `pathlib`.
- `src/extract.py` — generic, reusable download/copy/manifest functions, used for both datasets.
- First notebook (`01_extraction_exploration.ipynb`) — loads and eyeballs the raw data.
- Pushed to GitHub (`git remote add origin` + `git push -u origin main`).

### Mistakes hit + how they were fixed

| Problem | Cause | Fix |
|---|---|---|
| `mkdir -p ...` failed | Copied Bash/Linux syntax into PowerShell, which doesn't support `-p` or space-separated multi-path the same way | Used comma-separated paths (`mkdir a, b, c`) — PowerShell's `New-Item` already creates parent folders by default |
| Couldn't create `.gitignore` easily via File Explorer | Windows File Explorer resists creating files that start with a dot and have no extension | Created it via VS Code's Explorer panel "New File" instead, which has no such restriction |
| Kaggle auth flow didn't match instructions | Kaggle had switched from the old `kaggle.json` (username + key) format to a single API token (`KAGGLE_API_TOKEN`) | Adjusted `.env` to store the single token instead — `kagglehub` supports both auth methods automatically, no code changes needed |
| `.env.example` missing from `git status` | File wasn't actually saved correctly the first time (likely a naming/extension mismatch) | Recreated it carefully in VS Code, confirmed with `dir -Force` and `git status` before moving on |
| `ModuleNotFoundError: No module named 'src'` in notebook | Notebooks execute relative to their own folder (`notebooks/`), so they can't automatically see the `src/` folder next door | Added `sys.path.append(os.path.abspath(".."))` as the first cell in every notebook, going forward |
| Notebook created inside a duplicate nested `notebooks/notebooks/` folder | Accidental double-click/creation while navigating VS Code's Explorer | Dragged the file up one level, deleted the empty duplicate folder |
| `FileNotFoundError` reading `drivers.csv` | Guessed the filename instead of checking — actual file was named `F1_driver.csv` | Used `os.listdir(...)` to print real filenames instead of assuming |
| `NameError: name 'pd' is not defined` | Ran a later cell without running the earlier `import pandas as pd` cell first in that kernel session — kernel had also been restarted, wiping prior state | Learned the core notebook rule: cells only "remember" what's been *run*, not what's visually above them. Fixed by using **Restart + Run All** |

### Key lesson from Day 1
Notebook state is **execution-order dependent, not visual-order dependent**. Anytime something behaves unexpectedly (`NameError`, stale imports), the reliable fix is **Restart the kernel, then Run All** — this became a standing habit from here on.

---

## Day 2 — ETL Cleaning (`\N` handling, lap time parsing)

### What was built
- `src/transform.py`:
  - `clean_nulls(df)` — replaces literal `\N` strings (a MySQL-export null marker inherited by this dataset) and empty/whitespace strings with real `NaN` values, using regex.
  - `parse_lap_time(time_str)` — converts `"M:SS.mmm"` format lap times into total milliseconds as an integer, with defensive handling for nulls, already-numeric input, and malformed strings via `try/except`.
- Second notebook (`02_etl_cleaning.ipynb`), separated from Day 1's notebook to keep each notebook scoped to one pipeline stage.
- Verified `clean_nulls` against real data (`results.csv`) — confirmed null counts jumped from misleadingly-0 to real, explainable values after cleaning (10,953 missing finish positions from DNFs, 18,507 missing fastest-lap fields from older, less-instrumented race eras, etc.).
- Verified `parse_lap_time` against real lap times — spot-checked math by converting back to minutes and confirming it matched the original value.
- Built a loop (Cell 9) applying `clean_nulls` across **all 14 race-history CSVs at once**, saving each as a cleaned `.parquet` file in `data/processed/race_history/`, with a before/after null-count summary table.

### Mistakes hit + how they were fixed

| Problem | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'parse_lap_time'` | Function was added to `transform.py` *after* the notebook had already imported that module once — Python caches imports and doesn't auto-refresh them | Restarted the kernel to force a fresh read of the file. Later added `%load_ext autoreload` / `%autoreload 2` as a permanent fix so future edits pick up automatically |
| `ArrowKeyError: A type extension with name pandas.period already defined` on `.to_parquet(...)` | `pyarrow` (the library backing Parquet support) got into a conflicting state from being invoked more than once in the same live kernel session | Fixed with a clean **Restart + Run All**. Also added a defensive `shutil.rmtree()` step before the loop to clear out any partially-written output from a previous run |
| `NameError: name 'os' is not defined` | Ran a cell in isolation without running the earlier setup cell (`import os`) first in that session | Same root cause and fix as Day 1's `pd` error — Restart + Run All |

### Key lesson from Day 2
**Never trust that code "ran successfully" as proof it's correct** — always sanity-check against real-world expectations. Example: null counts after cleaning weren't just "higher," they were checked against known F1 facts (DNFs have no finish time, older eras didn't track fastest-lap data) to confirm the numbers made *sense*, not just that they changed.

Also: **DRY (Don't Repeat Yourself)** — rather than manually repeating the same 4–5 lines of cleaning code for 14 separate files, built one reusable loop. This is the difference between "code that works once" and "code that scales."

---

## Concepts Learned So Far (plain-language glossary)

- **Virtual environment (`venv`)** — an isolated Python installation per-project, so package versions don't conflict across different projects.
- **`.gitignore`** — tells Git which files to never track (secrets, generated data, environment folders).
- **Environment variables / `.env`** — a way to store secrets (like API keys) outside of your actual code, so they're never accidentally shared or committed.
- **`pathlib` / `os.path.join`** — safe, cross-platform ways to build file paths without hardcoding `/` vs `\`.
- **Regex (regular expressions)** — a pattern-matching language used to find/replace text based on shape rather than exact value (e.g., "anything that looks like `\N`").
- **`try/except`** — Python's way of attempting risky code and gracefully handling failure instead of crashing.
- **`.apply()`** — runs a function once across every row (or column) of a Pandas table.
- **List comprehension** (`[f for f in x if condition]`) — a compact way of writing a filtering loop.
- **Parquet vs CSV** — Parquet is a compressed, binary, columnar format that preserves data types (numbers stay numbers, nulls stay null) — unlike CSV, which flattens everything back to plain text.
- **Kernel state / execution order** — a notebook only "remembers" cells that have actually been run, in the order they were run — not the order they appear on the page. Restart + Run All guarantees a true, reproducible state.
- **DRY (Don't Repeat Yourself)** — writing reusable functions/loops instead of duplicating the same logic across multiple files or cells.

---

## Commands Cheat Sheet (Windows PowerShell)

```powershell
# Activate virtual environment
venv\Scripts\activate

# Run the extraction pipeline
python -m src.extract

# Check git status / commit / push
git status
git add .
git commit -m "feat: description here"
git push

# List files in a folder (including hidden/dot files)
dir -Force

# Install a missing package
pip install package-name
```

---

## Day 3 — Relational Database Setup & Star Schema Warehouse Modeling

### The core question this day answers
Days 1–2 got clean data sitting in Parquet files on disk. But Parquet files aren't a database — there's no way to run relational queries, enforce data integrity, or connect a BI tool like Tableau to a flat file the way you can to a real warehouse. Day 3's job: design and stand up an actual relational database that the cleaned data will be loaded into on Day 4.

---

### Decision 1: PostgreSQL vs DuckDB

Two real options existed: **DuckDB** (a Python-embedded database, zero server setup, just `pip install duckdb`) or **PostgreSQL** (a real client-server database requiring an actual installed service).

**Chose PostgreSQL**, reasoning through three angles:
- **Resume/job-market signal:** "PostgreSQL" appears constantly in data analyst job postings; DuckDB is newer and less universally expected.
- **Tableau compatibility:** Tableau has a mature, first-party, native PostgreSQL connector. DuckDB's Tableau connector is newer and community-maintained — more risk of friction during Day 7/8, the most visually-judged part of the whole project.
- **Production realism:** Postgres is closer to what real company data infrastructure looks like, versus DuckDB's more specialized embedded-analytics niche.

The trade-off accepted knowingly: Postgres requires a real installer, a running Windows service, and a password-protected superuser account — meaningfully more setup steps than DuckDB's one-line install. Worth it for what it unlocks later (Tableau, resume recognition).

### Installing and standing up PostgreSQL

1. Downloaded and ran the PostgreSQL 18 Windows installer (via EnterpriseDB), keeping all default components (Server, pgAdmin 4, Command Line Tools).
2. Set a superuser (`postgres`) password during install — stored securely, referenced later in `.env`.
3. Confirmed the install via `psql --version` in a fresh PowerShell window — required opening a *new* terminal window, since PATH environment variable changes don't apply to already-open terminals.
4. Confirmed the Postgres Windows service was running via the Services app (`postgresql-x64-18` status = Running).
5. Created a dedicated database for this project (kept isolated from any other Postgres database that might exist on the same machine):
   ```sql
   CREATE DATABASE f1_warehouse;
   ```
6. Verified it existed with `\l` (list all databases).

### Connecting Python to Postgres

Added database credentials to `.env` (gitignored) and a matching placeholder set to `.env.example` (committed):
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=f1_warehouse
DB_USER=postgres
DB_PASSWORD=********
```

Extended `src/config.py` to build a single connection string SQLAlchemy understands:
```python
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
```
**What this line is doing:** it's assembling a **connection string** — a single URL-shaped string that packs in everything SQLAlchemy needs to reach the database: which dialect (`postgresql`), which driver library to use underneath (`psycopg2`, installed back on Day 1), then username, password, host, port, and database name, all pulled from environment variables rather than hardcoded — so the real password never appears anywhere in committed code.

Verified the connection worked with a minimal test query, run from a notebook:
```python
from sqlalchemy import create_engine, text
from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    print(result.fetchone())
```
Output confirmed a real round-trip to the database: `('PostgreSQL 18.4 on x86_64-windows, ...)`.

**Why test with something this trivial first:** isolating "does the connection itself work" from "does my schema logic work" — if this simple query had failed, the problem would clearly be connection/credentials, not schema design. Testing the smallest possible piece first is a deliberate debugging habit, not a wasted step.

---

### Decision 2: Inspecting real columns before designing anything

Before writing a single line of schema, printed the actual column names from every source table that would feed the warehouse — deliberately avoiding designing against a guessed/generic template:
```python
tables_to_check = ["results", "races", "drivers", "constructors", "circuits", "status", "qualifying"]

for name in tables_to_check:
    df = pd.read_csv(f"../data/raw/race_history/{name}.csv")
    print(f"\n=== {name}.csv ===")
    print(df.columns.tolist())
```
This surfaced the real column names (e.g., `driverRef`, `circuitRef`, `positionOrder`) that the DDL below was built directly against — avoiding a mismatch that would only surface as an error during Day 4's load.

---

### Designing the Star Schema

**Grain decision — the most important call of the day:** one row in the primary fact table represents **one driver's result in one race**. This matches the natural grain already present in `results.csv`, so no aggregation or disaggregation was needed to define it.

**5 dimension tables** (the "who/what/where" descriptive tables):
| Dimension | Sourced from | Purpose |
|---|---|---|
| `dim_driver` | drivers.csv | driver biographical attributes |
| `dim_constructor` | constructors.csv | team/constructor attributes |
| `dim_circuit` | circuits.csv | track location and geography |
| `dim_status` | status.csv | finish/DNF status categories |
| `dim_race` | races.csv | one row per race event, references `dim_circuit` |

**2 fact tables** (the "what happened, with numbers" tables):
| Fact | Sourced from | Grain |
|---|---|---|
| `fact_race_results` | results.csv | one driver's result in one race |
| `fact_qualifying` | qualifying.csv | one driver's qualifying result in one race |

### Surrogate keys vs natural keys — the key modeling decision

Raw source data already has IDs (`driverId`, `raceId`, etc.) — these are **natural/business keys**, inherited from the original source system. Deliberately did **not** use them directly as primary keys. Instead, every warehouse table generates its own **surrogate key** — a simple auto-incrementing integer that exists only inside this warehouse — while keeping the original ID as a plain traceability column.

**Why this matters, not just "because Kimball says so":** it decouples the warehouse's internal structure from the source system (if Kaggle changed their ID scheme tomorrow, nothing downstream would break), and it's the standard, expected pattern in real dimensional modeling — a fact worth naming directly in interviews.

### Writing the DDL

`sql/ddl/01_dimensions.sql` — example (one of five, same pattern repeated for each):
```sql
DROP TABLE IF EXISTS dim_driver CASCADE;
CREATE TABLE dim_driver (
    driver_key SERIAL PRIMARY KEY,
    driver_id INTEGER NOT NULL UNIQUE,
    driver_ref VARCHAR(100),
    code VARCHAR(10),
    forename VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    dob DATE,
    nationality VARCHAR(100)
);
```

**Line-by-line meaning:**
- `DROP TABLE IF EXISTS dim_driver CASCADE;` — deletes the table first if it already exists, so the whole script is **idempotent** (safe to re-run any number of times, always ending in the same clean state, instead of erroring "table already exists" on a second run). `CASCADE` also drops anything depending on this table (e.g., foreign keys referencing it), necessary since tables reference each other.
- `driver_key SERIAL PRIMARY KEY` — the surrogate key. `SERIAL` tells Postgres to auto-generate an incrementing integer on every insert; `PRIMARY KEY` marks it as this table's unique identifier.
- `driver_id INTEGER NOT NULL UNIQUE` — the natural key, kept as a normal traceable column. `UNIQUE` blocks duplicate IDs from entering; `NOT NULL` blocks empty values.
- `VARCHAR(n)` / `DATE` — Postgres data types: bounded-length text, and a real calendar-date type (not just text — enables correct date math/sorting later).

`sql/ddl/02_facts.sql` — the fact table, showing foreign keys in action:
```sql
DROP TABLE IF EXISTS fact_race_results CASCADE;
CREATE TABLE fact_race_results (
    result_key SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL UNIQUE,
    race_key INTEGER NOT NULL REFERENCES dim_race(race_key),
    driver_key INTEGER NOT NULL REFERENCES dim_driver(driver_key),
    constructor_key INTEGER NOT NULL REFERENCES dim_constructor(constructor_key),
    status_key INTEGER REFERENCES dim_status(status_key),
    grid INTEGER,
    position INTEGER,
    position_order INTEGER,
    points NUMERIC(6,2),
    laps INTEGER,
    time_text VARCHAR(50),
    milliseconds INTEGER,
    fastest_lap INTEGER,
    rank INTEGER,
    fastest_lap_time_text VARCHAR(20),
    fastest_lap_ms INTEGER,
    fastest_lap_speed NUMERIC(8,3)
);
```

**New concepts introduced here:**
- **`REFERENCES dim_driver(driver_key)`** — a **foreign key constraint**. This tells Postgres "any value in this column must already exist in `dim_driver.driver_key`, no exceptions." This is the database itself physically enforcing referential integrity — a stronger version of the manual orphaned-ID checks written by hand in Pandas back on Day 2.
- **`NUMERIC(6,2)`** — a fixed-precision decimal (6 total digits, 2 after the decimal point) used for `points`. Chosen over a plain floating-point type specifically to avoid floating-point rounding errors on financial/scoring-style values — a deliberate, defensible engineering choice.
- **`fastest_lap_ms` column** — this column does **not exist** in the raw `results.csv`. It's added deliberately, ahead of time, as the destination for Day 2's `parse_lap_time()` output, which will be computed and inserted during Day 4's load. Designing a target schema to include planned engineered columns before the data lands is normal, intentional warehouse design.

### Running the DDL and verifying

Connected directly via `psql` and executed both files using the `\i` include command:
```sql
psql -U postgres -d f1_warehouse
\i sql/ddl/01_dimensions.sql
\i sql/ddl/02_facts.sql
```

Verified all 7 tables existed:
```sql
\dt
```

Inspected one table's full structure — columns, types, and all 4 foreign key constraints — to confirm the relationships were real and enforced, not just written in a script:
```sql
\d fact_race_results
```

The output confirmed `fact_race_results` correctly references `dim_race`, `dim_driver`, `dim_constructor`, and `dim_status` — proof the schema, not just the SQL syntax, was correct.

---

### Mistakes / non-issues hit

| Event | What actually happened | Resolution |
|---|---|---|
| `.env.example` was missing | Original Day 1 attempt never actually saved; went unnoticed since real `.env` worked fine and nothing depended on the example file functionally | Recreated it cleanly, confirmed via `git status` that it appeared as untracked while real `.env` stayed correctly hidden |
| Ran `\i sql/ddl/01_dimensions.sql` twice in a row | Not an error — re-ran out of habit/curiosity | Confirmed this was the *intended* safe behavior: `DROP TABLE IF EXISTS` meant the second run cleanly rebuilt everything with zero side effects, proving the idempotent design worked |

Worth noting explicitly: Day 3's actual schema design and database work had **no real blocking errors** — a contrast to Days 1–2, which were mostly fighting Windows/PowerShell/notebook environment friction rather than core data concepts. This suggests the earlier friction was genuinely tooling-related, not a sign of struggling with the underlying material.

---

### Key lessons from Day 3
1. **Grain is the first and most important decision** in any dimensional model — everything else (which columns are measures vs. attributes, how facts and dimensions relate) flows from correctly identifying what one fact row represents.
2. **Surrogate keys decouple your warehouse from source systems** and are the expected standard in real dimensional modeling (Kimball methodology) — not using them is a common beginner shortcut that signals inexperience.
3. **Foreign key constraints move data-quality enforcement from "checked manually after the fact" (Day 2's Pandas orphan checks) to "physically guaranteed by the database at insert time."** This is a meaningfully stronger integrity guarantee, and a good example to give if asked "how do you ensure data quality in a pipeline."
4. **Idempotent DDL scripts** (`DROP ... IF EXISTS ... CASCADE` before every `CREATE`) remove an entire category of "works once, breaks on re-run" bugs — a small pattern, cheap to apply, worth using as a default habit in any schema-authoring work going forward.

### New concepts learned (added to running glossary)
- **Grain** — the exact real-world event/entity one row in a fact table represents.
- **Surrogate key vs natural/business key** — auto-generated internal ID vs. the original source system's ID, kept for traceability.
- **Foreign key constraint** — database-enforced rule that a column's value must exist in a referenced table's key column.
- **Idempotent script** — produces the same end state no matter how many times it's re-run.
- **Connection string** — a single URL-formatted string bundling driver, credentials, host, port, and database name for a database connection.
- **`psql` shortcuts** — `\l` lists databases, `\dt` lists tables, `\d tablename` shows a table's full structure, `\i file.sql` runs a SQL file, `\q` exits.