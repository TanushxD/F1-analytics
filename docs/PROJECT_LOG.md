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

## Day 4 — Data Warehousing Operations, Primary/Foreign Keys, and Loading via SQLAlchemy

### The core question this day answers
Day 3 built an empty warehouse — 7 tables, correctly related, but with zero rows in them. Day 4's job: actually get Day 2's cleaned Parquet data into those tables, correctly translating natural keys (`driverId`, `raceId`) into the warehouse's own surrogate keys (`driver_key`, `race_key`) along the way.

---

### Building a shared database connection (`src/db.py`)

Rather than every script creating its own separate `create_engine(...)` call, built the SQLAlchemy engine **once**, in one small dedicated file, and imported it everywhere else needed:
```python
from sqlalchemy import create_engine
from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
```
**Why this deserves its own file:** if connection details ever change, there's exactly one place to fix it, instead of hunting through every script that touches the database. This pattern is sometimes called a "shared resource module."

---

### The load pattern: dimensions first, in dependency order

Wrote `src/load.py` with one function per dimension table. Example — `dim_driver`:
```python
def load_dim_driver():
    df = pd.read_parquet(RACE_HISTORY_DIR / "drivers.parquet")
    df = df.rename(columns={
        "driverId": "driver_id",
        "driverRef": "driver_ref",
    })
    df = df[["driver_id", "driver_ref", "code", "forename", "surname", "dob", "nationality"]]
    df.to_sql("dim_driver", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_driver")
```

**What each step does:**
- `.rename(columns={...})` — Parquet files kept Kaggle's original `camelCase` column names; the warehouse DDL uses `snake_case` (Postgres convention). Renamed to match exactly before insertion.
- `df[[...]]` — selects only the columns the warehouse table actually has, silently dropping anything extra (like `url`, present in the raw CSV but not part of the DDL).
- `df.to_sql("dim_driver", engine, if_exists="append", index=False)` — the actual insert. `if_exists="append"` adds rows to the existing (already-created-by-DDL) table, rather than dropping/recreating it. `index=False` avoids inserting Pandas' internal row-numbering as a spurious extra column.

### The "translation dictionary" pattern — mapping natural keys to surrogate keys

Since surrogate keys are auto-generated by Postgres on insert, there's no way to know them in advance — so after loading a dimension, its table is read back out to build a lookup:
```python
def get_key_mapping(table_name: str, natural_col: str, surrogate_col: str) -> dict:
    """Reads a dimension table back out and builds a {natural_id: surrogate_key} lookup dict."""
    query = f"SELECT {natural_col}, {surrogate_col} FROM {table_name}"
    df = pd.read_sql(query, engine)
    return dict(zip(df[natural_col], df[surrogate_col]))
```
**Mechanics:** `pd.read_sql(query, engine)` runs a raw SQL query and returns a DataFrame — the reverse direction of `to_sql`. `zip(col_a, col_b)` pairs the two columns element-by-element; wrapping in `dict()` turns those pairs into a lookup table, e.g. `{123: 1, 456: 2}` meaning "Kaggle's `driverId` 123 became our `driver_key` 1."

This mapping is why **load order matters**: `dim_race` has a foreign key to `dim_circuit`, so `load_dim_race()` calls `get_key_mapping("dim_circuit", ...)` *first*, translates `circuitId → circuit_key` via `.map()`, and only then inserts:
```python
def load_dim_race():
    circuit_mapping = get_key_mapping("dim_circuit", "circuit_id", "circuit_key")
    df = pd.read_parquet(RACE_HISTORY_DIR / "races.parquet")
    df = df.rename(columns={"raceId": "race_id", "circuitId": "circuit_id", "date": "race_date"})
    df["circuit_key"] = df["circuit_id"].map(circuit_mapping)
    df = df[["race_id", "circuit_key", "year", "round", "name", "race_date"]]
    df.to_sql("dim_race", engine, if_exists="append", index=False)
```
Load order enforced explicitly: independent dimensions first (`driver`, `constructor`, `circuit`, `status`), then dependent dimensions (`race`, which needs `circuit` already loaded).

**Result:** all 5 dimensions loaded cleanly on first attempt, row counts matching Day 2's cleaned Parquet files exactly (861 drivers, 212 constructors, 77 circuits, 139 statuses, 1125 races).

---

### Loading fact tables — the more complex half

Fact tables need *multiple* simultaneous key translations. `load_fact_race_results()`:
```python
def load_fact_race_results():
    driver_map = get_key_mapping("dim_driver", "driver_id", "driver_key")
    constructor_map = get_key_mapping("dim_constructor", "constructor_id", "constructor_key")
    race_map = get_key_mapping("dim_race", "race_id", "race_key")
    status_map = get_key_mapping("dim_status", "status_id", "status_key")

    df = pd.read_parquet(RACE_HISTORY_DIR / "results.parquet")
    df = df.rename(columns={
        "resultId": "result_id", "positionOrder": "position_order", "time": "time_text",
        "fastestLap": "fastest_lap", "fastestLapTime": "fastest_lap_time_text",
        "fastestLapSpeed": "fastest_lap_speed",
    })

    df["fastest_lap_ms"] = df["fastest_lap_time_text"].apply(parse_lap_time)

    df["driver_key"] = df["driverId"].map(driver_map)
    df["constructor_key"] = df["constructorId"].map(constructor_map)
    df["race_key"] = df["raceId"].map(race_map)
    df["status_key"] = df["statusId"].map(status_map)

    rows_before = len(df)
    df = df.dropna(subset=["driver_key", "constructor_key", "race_key"])
    rows_after = len(df)
    if rows_before != rows_after:
        logger.warning(f"Dropped {rows_before - rows_after} rows with unmatched keys in fact_race_results")

    df = df[[
        "result_id", "race_key", "driver_key", "constructor_key", "status_key",
        "grid", "position", "position_order", "points", "laps",
        "time_text", "milliseconds", "fastest_lap", "rank",
        "fastest_lap_time_text", "fastest_lap_ms", "fastest_lap_speed"
    ]]
    df.to_sql("fact_race_results", engine, if_exists="append", index=False)
```

**New elements here:**
- **`df["fastest_lap_ms"] = df["fastest_lap_time_text"].apply(parse_lap_time)`** — Day 2's lap-time parser, written and unit-tested two days earlier, now runs across the full real dataset as part of the actual production load — not a notebook test cell anymore.
- **`df.dropna(subset=["driver_key", "constructor_key", "race_key"])`** — a defensive safety step. If `.map()` couldn't find a match for some natural key (returning `NaN`), inserting that row would violate a foreign key constraint and crash the entire load. Proactively dropping unmatched rows *before* attempting insert, with a logged warning showing how many (if any) were affected, turns a potential hard crash into a graceful, visible, recoverable situation.
- `load_fact_qualifying()` follows an identical pattern, translating three keys instead of four and parsing three lap-time columns (`q1`, `q2`, `q3`) instead of one.

**Result on first real attempt:** `fact_race_results` loaded 26,759 rows, `fact_qualifying` loaded 10,494 rows — matching Day 2's source row counts exactly, meaning zero rows were dropped and every natural key successfully matched.

---

### Bug hit: `UniqueViolation` on re-run

**What happened:** after the initial successful dimension load, `run_dimension_load()` (later renamed `run_full_load()`) was re-run to add the fact-loading step. Since `to_sql(..., if_exists="append")` always adds rows rather than checking for existing ones, it attempted to re-insert `driver_id=1` (Lewis Hamilton) on top of data that already existed from the first run — and Postgres's `UNIQUE` constraint on `dim_driver.driver_id` (set up deliberately on Day 3) correctly rejected the duplicate:
```
UniqueViolation: duplicate key value violates unique constraint "dim_driver_driver_id_key"
DETAIL:  Key (driver_id)=(1) already exists.
```

**Root cause:** the load pipeline had no mechanism to reset/clear existing data before re-loading — unlike the Day 3 DDL scripts, which were explicitly designed to be idempotent via `DROP TABLE IF EXISTS`. The load pipeline needed the same idempotency at the data level.

**Fix — added a `reset_tables()` step:**
```python
def reset_tables():
    """Clears all warehouse tables (in dependency order) so the load is safe to re-run from scratch."""
    tables_in_dependency_order = [
        "fact_qualifying", "fact_race_results",
        "dim_race", "dim_status", "dim_circuit", "dim_constructor", "dim_driver",
    ]
    with engine.begin() as conn:
        for table in tables_in_dependency_order:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    logger.info("All warehouse tables truncated and reset.")


def run_full_load():
    reset_tables()
    load_dim_driver()
    load_dim_constructor()
    load_dim_circuit()
    load_dim_status()
    load_dim_race()
    load_fact_race_results()
    load_fact_qualifying()
```

**New concepts here:**
- **`TRUNCATE TABLE ... RESTART IDENTITY CASCADE`** — `TRUNCATE` clears all rows (faster than `DELETE FROM` for large tables). `RESTART IDENTITY` resets the `SERIAL` auto-increment counter back to 1 — without this, a fresh load would generate surrogate keys continuing from wherever the previous run left off (e.g., `driver_key` starting at 862 instead of 1) even on an empty table. `CASCADE` also truncates anything with a foreign key pointing to the table being cleared.
- **`with engine.begin() as conn:`** — wraps the truncation loop in a database transaction that automatically commits on success or rolls back on failure, preventing a half-cleared warehouse state if something failed partway through the reset.

After this fix, `run_full_load()` ran cleanly end-to-end from a fresh state, producing identical, correct row counts every time it's re-run — the load pipeline is now genuinely idempotent, matching the same design principle already applied to the Day 3 DDL.

### Related tooling snag: stale/renamed function references
While fixing the above, hit two secondary but related errors:
- `ImportError: cannot import name 'run_dimension_load'` — a leftover notebook cell still referenced the function's old pre-rename name (`run_dimension_load` → `run_full_load`).
- `NameError: name 'reset_tables' is not defined` — `%autoreload 2` is reliable at picking up *edits* to existing functions, but sometimes fails to register a **brand-new** function/import added to a file. In practice this meant relying on **Restart + Run All** rather than autoreload alone whenever new functions (not just edited ones) were introduced.

---

### Verification performed (not just "it ran")

1. **Row count cross-check** against Day 2's cleaned Parquet summary — all 7 tables matched exactly.
2. **Explicit orphan-key check**, proving referential integrity rather than assuming it:
   ```sql
   SELECT COUNT(*) 
   FROM fact_race_results f
   LEFT JOIN dim_driver d ON f.driver_key = d.driver_key
   WHERE d.driver_key IS NULL
   ```
   Returned `0` — confirmed every fact row's `driver_key` correctly resolves to a real driver.
3. **Spot-check via a real multi-table JOIN** — queried Lewis Hamilton's early race results by joining `fact_race_results → dim_driver → dim_race`, confirming human-readable, correctly-related data comes back out the other end. This query incidentally surfaced a genuine data nuance: a second, unrelated driver named "Duncan Hamilton" (1950s) shares the surname — a reminder that `WHERE surname = 'Hamilton'` is a broad filter, not proof of full precision; a good lesson in query specificity carried into Day 5.

---

### Key lessons from Day 4
1. **Idempotency needs to be designed at every layer, not just the schema layer.** Day 3's DDL was safely re-runnable; Day 4's load pipeline initially wasn't — `reset_tables()` closed that gap. "How do you make a pipeline safe to re-run" is now something with a concrete, demonstrated answer.
2. **Surrogate key generation requires a round-trip:** insert dimensions first, read their auto-generated keys back out, build a translation dictionary, then use it to correctly populate fact tables. This sequencing (not just "insert everything") is the actual mechanics behind making a star schema load work.
3. **Never assume a JOIN or constraint is correct — query for proof.** The orphan-check query is a concrete, repeatable way to demonstrate referential integrity, not just claim it.
4. **`RESTART IDENTITY` matters specifically because of `SERIAL` surrogate keys** — a detail easy to overlook, but skipping it would silently produce inconsistent surrogate key values across repeated loads.

### New concepts learned (added to running glossary)
- **Shared resource module** — a single small file (e.g. `src/db.py`) creating one reusable resource (a DB engine), imported everywhere else needed, instead of recreating it repeatedly.
- **`.map(dictionary)`** — applies a dictionary lookup across an entire Pandas column at once, row by row.
- **`TRUNCATE ... RESTART IDENTITY CASCADE`** — clears a table's rows, resets its auto-increment counter, and cascades to dependent tables.
- **Database transaction (`engine.begin()`)** — a block of operations that either all succeed together (commit) or all fail together (rollback), preventing partially-applied changes.
- **Orphan-check query pattern** (`LEFT JOIN ... WHERE right_table.key IS NULL`) — the standard SQL technique for proving referential integrity between two tables.