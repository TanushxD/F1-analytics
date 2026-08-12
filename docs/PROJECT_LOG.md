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

## Day 5 — Advanced SQL Analytics (Window Functions, CTEs, Complex Aggregations)

### The core question this day answers
Day 4 proved the warehouse was structurally correct (referential integrity, row counts). Day 5's job: prove it's *analytically useful* — write real SQL that answers real F1 questions, using techniques (window functions, CTEs, self-joins) that go meaningfully beyond basic `SELECT`/`WHERE`/`GROUP BY`.

All 5 queries live as standalone, reviewable `.sql` files in `sql/analytics_queries/`, executed from notebooks by reading the file and running it via SQLAlchemy — keeping SQL skill visibly separate from Python, rather than buried as string literals inside application code.

---

### Query 1 — Driver Championship Progression (`01_championship_progression.sql`)

**Goal:** cumulative points per driver per season, plus a live championship rank recalculated after every race.

```sql
WITH driver_season_points AS (
    SELECT
        d.driver_key, d.forename, d.surname, r.year, r.round, r.race_date, f.points,
        SUM(f.points) OVER (
            PARTITION BY d.driver_key, r.year
            ORDER BY r.round
        ) AS cumulative_points
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
)
SELECT
    forename, surname, year, round, race_date, points, cumulative_points,
    RANK() OVER (
        PARTITION BY year, round
        ORDER BY cumulative_points DESC
    ) AS championship_rank_after_race
FROM driver_season_points
WHERE year = 2023
ORDER BY round, championship_rank_after_race;
```

**Key concepts:**
- **CTE (`WITH ... AS (...)`)** — a named, temporary result set, used here to separate "compute the running total" from "rank based on that total" into two readable stages instead of one tangled query.
- **Window function (`SUM(...) OVER (...)`)** — unlike a normal aggregate, a window function computes a value *without* collapsing rows — every original row stays visible, each gaining its own running total.
- **`PARTITION BY driver_key, year`** — restarts the running total separately for each driver-season combination, instead of one meaningless total across everyone.
- **`RANK()`** — assigns standings with ties sharing a rank and the next rank skipping accordingly (1, 2, 2, 4) — matching how real championship standings work.

**Validation:** round 1 output exactly matched real 2023 Bahrain GP results and the FIA points table (Verstappen 25, Pérez 18, Alonso 15, ...). Confirmed 10 drivers tied at 0 points all correctly shared `rank = 11`.

---

### Query 2 — Constructor Reliability Rate (`02_reliability_rate.sql`)

**Goal:** mechanical failure rate and finish rate per constructor per season — feeds directly into Day 6 feature engineering.

**Challenge:** `dim_status` has 141 distinct granular status values (Engine, Gearbox, Hydraulics, +1 Lap, Disqualified, etc.) — no clean "DNF: Yes/No" flag exists in the source data. Checked the real values first (`SELECT * FROM dim_status`) before writing any categorization logic, rather than guessing generic status names.

```sql
WITH categorized_results AS (
    SELECT
        c.constructor_key, c.name AS constructor_name, r.year, f.result_id, s.status,
        CASE
            WHEN s.status = 'Finished' OR s.status LIKE '+%Lap%' THEN 'Finished'
            WHEN s.status IN ('Accident', 'Collision', 'Spun off', 'Collision damage') THEN 'Accident'
            WHEN s.status IN ('Disqualified', 'Excluded', 'Did not qualify', ...) THEN 'Other'
            ELSE 'Mechanical'
        END AS status_category
    FROM fact_race_results f
    JOIN dim_constructor c ON f.constructor_key = c.constructor_key
    JOIN dim_race r ON f.race_key = r.race_key
    JOIN dim_status s ON f.status_key = s.status_key
),
constructor_season_summary AS (
    SELECT
        constructor_key, constructor_name, year,
        COUNT(*) AS total_entries,
        COUNT(*) FILTER (WHERE status_category = 'Mechanical') AS mechanical_failures,
        COUNT(*) FILTER (WHERE status_category = 'Finished') AS finishes
    FROM categorized_results
    GROUP BY constructor_key, constructor_name, year
)
SELECT
    constructor_name, year, total_entries, mechanical_failures,
    ROUND(mechanical_failures::NUMERIC / total_entries * 100, 1) AS mechanical_failure_rate_pct,
    finishes,
    ROUND(finishes::NUMERIC / total_entries * 100, 1) AS finish_rate_pct
FROM constructor_season_summary
WHERE year = 2023
ORDER BY mechanical_failure_rate_pct DESC;
```

**Key concepts:**
- **`CASE WHEN ... THEN ... ELSE ... END`** — SQL's if/elif/else. Checked top-to-bottom; unmatched "Other" statuses deliberately fall through to `ELSE 'Mechanical'`, avoiding the need to explicitly list 100+ mechanical failure sub-types by hand.
- **`LIKE '+%Lap%'`** — pattern matching; `%` matches any characters, catching every `+N Lap(s)` status without 30 separate `OR` conditions.
- **`COUNT(*) FILTER (WHERE ...)`** — a conditional count computed in a single pass, cleaner than the older `SUM(CASE WHEN x THEN 1 ELSE 0 END)` pattern (worth recognizing both, since older codebases often use the latter).
- **`::NUMERIC` type cast** — without it, `mechanical_failures / total_entries` performs integer division (e.g. `3/10 = 0`, not `0.3`) — a classic SQL gotcha. Casting to `NUMERIC` first forces correct decimal division.

**Validation:** Red Bull 2023 showed a **0.0% mechanical failure rate** — matching their historically dominant, near-perfect-reliability season (21 wins of 22 races). Ferrari topped the failure-rate list (11.4%), consistent with their well-documented 2023 reliability struggles.

---

### Query 3 — Grid-to-Finish Delta / "Overtaking Index" (`03_grid_delta.sql`)

**Goal:** average positions gained/lost between qualifying grid and race finish, per driver per season.

```sql
WITH race_deltas AS (
    SELECT
        d.driver_key, d.forename, d.surname, r.year, f.race_key, f.grid, f.position_order,
        (f.grid - f.position_order) AS positions_gained
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
    WHERE f.grid > 0
),
driver_season_avg AS (
    SELECT
        driver_key, forename, surname, year,
        COUNT(*) AS races_completed,
        ROUND(AVG(positions_gained), 2) AS avg_positions_gained
    FROM race_deltas
    GROUP BY driver_key, forename, surname, year
    HAVING COUNT(*) >= 5
)
SELECT
    forename, surname, year, races_completed, avg_positions_gained,
    DENSE_RANK() OVER (PARTITION BY year ORDER BY avg_positions_gained DESC) AS overtaking_rank
FROM driver_season_avg
WHERE year = 2023
ORDER BY overtaking_rank;
```

**Key concepts:**
- **`WHERE f.grid > 0`** — excludes pit-lane starts (`grid = 0`), which would otherwise badly distort the "positions gained" baseline.
- **`HAVING COUNT(*) >= 5`** — filters on an aggregate result, which `WHERE` cannot do (it runs *before* grouping exists). Excludes drivers with too few races that season (e.g., mid-season substitutes) to produce a meaningful average.
- **`DENSE_RANK()` vs `RANK()`** — `DENSE_RANK()` doesn't skip numbers after ties (1, 2, 2, 3 instead of 1, 2, 2, 4), producing a cleaner leaderboard for this metric.

**Validation:** Pérez (+2.50) and Verstappen (+1.91) topped the list — consistent with Red Bull's car dominance letting both drivers routinely recover from grid penalties/qualifying slumps. Leclerc (−2.57) and Hülkenberg (−3.21) at the bottom matched their known strong-qualifying/weaker-race-pace patterns that season.

---

### Query 4 — Rolling Form Index (`04_rolling_form.sql`)

**Goal:** a 5-race trailing average of points, to capture recent form rather than season-long totals — direct setup for Day 6's feature engineering.

```sql
WITH driver_race_points AS (
    SELECT d.driver_key, d.forename, d.surname, r.year, r.round, r.race_date, f.points
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
    WHERE r.year = 2023
)
SELECT
    forename, surname, round, race_date, points,
    ROUND(
        AVG(points) OVER (
            PARTITION BY driver_key
            ORDER BY round
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_5race_form
FROM driver_race_points
WHERE surname = 'Verstappen'
ORDER BY round;
```

**Key concept — the frame clause:** `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` restricts the window function to the current row plus the 4 immediately before it (5 rows total). At round 1, no prior rows exist, so the "rolling average" is just that round's own points; the window fills in gradually and becomes a genuine 5-race average from round 5 onward — Postgres handles this partial-window behavior automatically, equivalent to `min_periods=1` in a Pandas rolling window.

**Validation:** round 15 of 2023 (Singapore GP — Verstappen's only non-win that season, finishing P5) showed `points = 10.0`. The rolling average visibly dipped from `25.40` to `22.20` in response — correctly absorbing one anomalous result into the recent-form trend rather than treating it as noise, exactly the behavior a rolling average is meant to produce.

---

### Query 5 — Teammate Head-to-Head (`05_teammate_head_to_head.sql`)

**Goal:** for each constructor, compare finishing positions between teammates race-by-race, isolating driver skill from car performance.

```sql
WITH teammate_pairs AS (
    SELECT
        f1.race_key, r.year, f1.constructor_key,
        f1.driver_key AS driver_a_key, f1.position_order AS driver_a_position,
        f2.driver_key AS driver_b_key, f2.position_order AS driver_b_position
    FROM fact_race_results f1
    JOIN fact_race_results f2
        ON f1.race_key = f2.race_key
       AND f1.constructor_key = f2.constructor_key
       AND f1.driver_key < f2.driver_key
    JOIN dim_race r ON f1.race_key = r.race_key
),
head_to_head AS (
    SELECT
        constructor_key, year, driver_a_key, driver_b_key,
        COUNT(*) FILTER (WHERE driver_a_position < driver_b_position) AS a_wins,
        COUNT(*) FILTER (WHERE driver_b_position < driver_a_position) AS b_wins,
        COUNT(*) AS races_together
    FROM teammate_pairs
    GROUP BY constructor_key, year, driver_a_key, driver_b_key
)
SELECT
    c.name AS constructor_name, h.year,
    da.forename || ' ' || da.surname AS driver_a,
    db.forename || ' ' || db.surname AS driver_b,
    h.a_wins, h.b_wins, h.races_together
FROM head_to_head h
JOIN dim_constructor c ON h.constructor_key = c.constructor_key
JOIN dim_driver da ON h.driver_a_key = da.driver_key
JOIN dim_driver db ON h.driver_b_key = db.driver_key
WHERE h.year = 2023
ORDER BY h.races_together DESC;
```

**Key concepts:**
- **Self-join** — joining `fact_race_results` to itself (aliased `f1`/`f2`) to compare two different drivers' results within the same race and team.
- **`f1.driver_key < f2.driver_key`** — a deliberate inequality in the join condition that simultaneously prevents a driver being paired with themselves and prevents each pair appearing twice (once each direction).
- **`||` string concatenation** — combines `forename` and `surname` into one readable display column.

**Validation:** Verstappen led Pérez 20–2 (matching Pérez's documented second-half 2023 slump); Norris led rookie teammate Piastri 17–5; Alonso led Stroll 18–4 (Alonso's strong comeback season); Leclerc edged Sainz 12–10 in a genuinely close intra-team battle — all consistent with real 2023 results. Notably, AlphaTauri correctly appeared as **three separate pairings** (10 + 7 + 5 = 22 races) reflecting a real mid-season driver swap (de Vries → Ricciardo → Lawson) — the self-join handled this correctly without any special-case logic.

---

### Key lessons from Day 5
1. **Window functions compute per-row values without collapsing rows** — the core distinction from `GROUP BY` aggregation, and the foundation for running totals, rankings, and rolling averages.
2. **`WHERE` filters before aggregation; `HAVING` filters after** — a distinction with no equivalent in basic Pandas filtering, and a common SQL interview question.
3. **Real categorical data is messy** — 141 status values had to be manually bucketed via `CASE WHEN`, not assumed to arrive pre-cleaned. Checking real values before writing categorization logic (same habit as Day 3's column-checking before DDL) avoided guessing wrong.
4. **Self-joins solve "compare two rows from the same table"** problems — a technique with no direct single-table equivalent, essential for any head-to-head/pairwise comparison.
5. **Numerically validating results against known real-world facts** (Red Bull's perfect reliability, Verstappen's Singapore loss, the Pérez/Verstappen head-to-head) is a stronger correctness check than just confirming a query runs without error — this is the same "does this make real-world sense" discipline applied back in Day 2's null-count validation, now applied to SQL output

### New concepts learned (added to running glossary)
- **CTE (`WITH ... AS (...)`)** — a named, temporary, reusable result set within a single query.
- **Window function (`... OVER (...)`)** — computes a value per row without collapsing rows, unlike a normal aggregate.
- **Frame clause (`ROWS BETWEEN ... AND ...`)** — restricts a window function to a specific sliding range of rows relative to the current one (used for rolling averages).
- **`RANK()` vs `DENSE_RANK()`** — `RANK()` skips numbers after ties; `DENSE_RANK()` does not.
- **`HAVING`** — filters on the result of an aggregate function, after grouping; distinct from `WHERE`, which filters before grouping.
- **`FILTER (WHERE ...)`** — computes a conditional aggregate (e.g. conditional `COUNT`) in a single pass.
- **Type cast (`::NUMERIC`)** — explicitly converts a value's type, needed here to avoid integer division truncating a percentage calculation to 0.
- **Self-join** — joining a table to itself (via aliases) to compare rows within the same table, e.g. teammates in the same race.

## Day 6 — Python Feature Engineering (Form Indexes, Reliability Metrics, Predictive Signals)

### The core question this day answers
Day 5 proved a set of analytical metrics were meaningful *in SQL*. Day 6's job: reproduce the same analytical thinking in Python/Pandas — needed because real feature engineering for modeling often has to live in Python, not SQL — and prove both versions agree, using the SQL results from Day 5 as a correctness baseline rather than trusting the Pandas version blindly.

All features pull data **out of the warehouse** (not the raw CSVs), reinforcing that the warehouse — not the original Kaggle files — is now the single source of truth for downstream work.

---

### Base data loader

```python
def load_results_base(engine) -> pd.DataFrame:
    """Pulls a clean, joined driver-result-race base table straight from the warehouse."""
    query = """
        SELECT
            f.result_id, d.driver_key, d.forename, d.surname,
            c.constructor_key, c.name AS constructor_name,
            r.race_key, r.year, r.round, r.race_date,
            f.grid, f.position_order, f.points, s.status
        FROM fact_race_results f
        JOIN dim_driver d ON f.driver_key = d.driver_key
        JOIN dim_constructor c ON f.constructor_key = c.constructor_key
        JOIN dim_race r ON f.race_key = r.race_key
        JOIN dim_status s ON f.status_key = s.status_key
        ORDER BY d.driver_key, r.race_date
    """
    return pd.read_sql(query, engine)
```
Built once, reused by every feature function, avoiding repeated JOIN logic. The `ORDER BY d.driver_key, r.race_date` is load-bearing, not cosmetic — every rolling/cumulative calculation downstream assumes chronological order per driver.

---

### Feature 1 — Rolling Form Index

```python
def compute_rolling_form(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()
    df["rolling_form_index"] = (
        df.groupby(["driver_key", "year"])["points"]
        .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
    )
    return df
```

**Mechanics:** `.groupby(["driver_key", "year"])` groups by driver *and* season; `.transform(lambda x: x.rolling(window=5, min_periods=1).mean())` computes a trailing 5-race average within each group, returning one value per row (`.transform`, not `.apply`, specifically to preserve row count/shape). `min_periods=1` allows partial windows early in a season, mirroring SQL's automatic `ROWS BETWEEN 4 PRECEDING` behavior at round 1–4.

### Bug hit: cross-season bleed

**First version** grouped only by `driver_key` (no `year`), producing values that didn't match Day 5's SQL output for early-season rounds (round 1: SQL said `25.00`, Pandas said `21.6`). Root cause: the rolling window was sliding across a driver's entire career uninterrupted by season boundaries, quietly blending in late-2022 races into "round 1 of 2023."

**Fix:** changed `df.groupby("driver_key")` to `df.groupby(["driver_key", "year"])`, forcing the rolling window to reset at every season boundary — mirroring what `WHERE year = 2023` had already done inside Day 5's SQL CTE, before its window function ran.

**Result after fix:** Pandas output matched Day 5's SQL output exactly, round-for-round, including the anomalous Singapore 2023 dip (round 15, Verstappen's only non-win, points dropped to 10.0, `rolling_form_index` correctly dipped from 25.40 to 22.20 in response).

### Unit tests written (`tests/test_features.py`)

```python
def test_rolling_form_no_lookahead_bias():
    sample_data = pd.DataFrame({
        "driver_key": [1, 1, 1, 1, 1],
        "year": [2023, 2023, 2023, 2023, 2023],
        "race_date": pd.to_datetime(["2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"]),
        "points": [10, 20, 30, 40, 50],
    })
    result = compute_rolling_form(sample_data, window=3)
    expected = [10.0, 15.0, 20.0, 30.0, 40.0]
    for i, exp_value in enumerate(expected):
        assert abs(result.iloc[i]["rolling_form_index"] - exp_value) < 0.001


def test_rolling_form_resets_per_season():
    sample_data = pd.DataFrame({
        "driver_key": [1, 1, 1],
        "year": [2022, 2023, 2023],
        "race_date": pd.to_datetime(["2022-11-01", "2023-01-01", "2023-02-01"]),
        "points": [100, 10, 20],
    })
    result = compute_rolling_form(sample_data, window=5)
    row_2023_first = result[(result["year"] == 2023)].iloc[0]
    assert row_2023_first["rolling_form_index"] == 10.0
```
Test 1 hand-computes expected rolling values against a known input sequence and asserts an exact (tolerance-bounded) match, directly proving no future value leaks into an earlier row. Test 2 directly targets the exact bug just fixed — a leftover high value from the previous season must not bleed into the first race of a new one.

### Tooling snag: `pytest` path resolution differs from notebooks

Running `pytest tests/test_features.py` failed with `ModuleNotFoundError: No module named 'src'`, despite using the same `sys.path.append(os.path.abspath(".."))` line that fixes this in notebooks. **Root cause:** notebooks execute from inside `notebooks/`, so `..` correctly climbs to the project root — but `pytest` was invoked from the project root itself, so the identical `..` climbed one level *too high* (`Music\` instead of `Music\F1-analytics\`).

**Fix:** created `pytest.ini` at the project root:
```ini
[pytest]
pythonpath = .
```
This tells pytest to add the project root to the import path directly, regardless of which subfolder a test happens to invoke it from — a cleaner, more portable fix than manual `sys.path` patching, which is fragile and tool/location-dependent. Removed the now-incorrect `sys.path.append` line from the test file entirely.

**Lesson:** the same import statement can require different fixes depending on which tool runs it (notebook vs. pytest vs. plain script), because each starts from a different working directory. `pytest.ini` with `pythonpath = .` is the standard, tool-agnostic fix.

Both tests passed after the fixes:
```
tests/test_features.py::test_rolling_form_no_lookahead_bias PASSED
tests/test_features.py::test_rolling_form_resets_per_season PASSED
```

---

### Feature 2 — Reliability Rate

```python
def categorize_status(status: str) -> str:
    """Buckets raw F1 status text into broad categories — mirrors the CASE WHEN logic
    from Day 5's SQL reliability query, kept consistent across both tools."""
    if status == "Finished" or ("Lap" in status and status.startswith("+")):
        return "Finished"
    if status in ("Accident", "Collision", "Spun off", "Collision damage"):
        return "Accident"
    other_statuses = {
        "Disqualified", "Excluded", "Did not qualify", "Did not prequalify",
        "Not classified", "Withdrew", "Not restarted", "Underweight",
        "Safety concerns", "107% Rule", "Safety", "Injured", "Injury",
        "Fatal accident", "Eye injury", "Driver unwell", "Illness", "Physical",
    }
    if status in other_statuses:
        return "Other"
    return "Mechanical"


def compute_reliability_rate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()
    df["status_category"] = df["status"].apply(categorize_status)
    df["is_finished"] = (df["status_category"] == "Finished").astype(int)
    df["races_so_far"] = df.groupby(["driver_key", "year"]).cumcount() + 1
    df["finishes_so_far"] = df.groupby(["driver_key", "year"])["is_finished"].cumsum()
    df["reliability_rate"] = round(df["finishes_so_far"] / df["races_so_far"] * 100, 1)
    return df
```

**Deliberate design choice:** `categorize_status` is a direct, rule-for-rule translation of Day 5's SQL `CASE WHEN` block — same category boundaries in both tools, so any mismatch found later would represent a genuine bug rather than a false discrepancy from differently-defined categories.

**Mechanics:** `(condition).astype(int)` turns a boolean Series into 1/0 flags, summable/averageable directly. `.groupby(...).cumcount() + 1` numbers races within each driver-season group starting at 1 ("how many races into this season, for this driver"). `.groupby(...)["is_finished"].cumsum()` gives a running total of finishes. Dividing the two produces a **season-to-date** reliability percentage that updates after every race — a more useful predictive feature than a single static end-of-season number.

**Validation:** by the final race of 2023, Verstappen showed `reliability_rate = 100.0`, Pérez showed `90.9` — consistent with Day 5's team-level finding of a 0% *mechanical* failure rate for Red Bull (Pérez's dropped points came from accidents, not mechanical failures — a distinction `categorize_status` correctly preserves as a separate "Accident" bucket).

**Pandas trap caught along the way:** initially used `.tail(10)` on a filtered-but-unsorted-by-race-date DataFrame expecting "last 10 races across the team," but since the data was sorted by `driver_key` first, `.tail(10)` returned only one driver's rows. Fixed with `.groupby("surname").tail(1)` — "last row of each group" — the correct pattern for per-group "most recent" lookups, distinct from `.tail(n)` on a flat frame.

---

### Feature 3 — Grid Delta (with a running/expanding trend)

```python
def compute_grid_delta(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()
    df["grid_delta"] = df["grid"] - df["position_order"]
    valid_grid = df["grid"] > 0
    df.loc[valid_grid, "grid_delta_running_avg"] = (
        df[valid_grid]
        .groupby(["driver_key", "year"])["grid_delta"]
        .transform(lambda x: x.expanding(min_periods=1).mean())
    )
    return df
```

**New concept — `.expanding()` vs `.rolling()`:** `.rolling(window=5)` always looks at a fixed-size sliding window (last 5 races only). `.expanding()` instead grows to include every race so far within the group — a genuinely different signal ("cumulative overtaking ability this season," not "recent-5-race form"). `valid_grid = df["grid"] > 0` excludes pit-lane starts (no real grid position), matching Day 5's SQL filter; using `.loc[valid_grid, ...]` leaves excluded rows as `NaN` rather than dropping them from the DataFrame outright.

**Validation:** final-round `grid_delta_running_avg` for Verstappen 2023 came out to `1.909091`, matching Day 5's SQL result (`1.91`) almost exactly.

---

### Feature 4 — Teammate Delta

```python
def compute_teammate_delta(df: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(df, on=["race_key", "constructor_key"], suffixes=("", "_teammate"))
    merged = merged[merged["driver_key"] != merged["driver_key_teammate"]]
    merged["teammate_finish_delta"] = (
        merged["position_order_teammate"] - merged["position_order"]
    )
    return merged[[
        "driver_key", "race_key", "year", "round", "forename", "surname",
        "constructor_name", "position_order", "driver_key_teammate",
        "position_order_teammate", "teammate_finish_delta"
    ]]
```

**New concept — self-merge:** the Pandas equivalent of Day 5's SQL self-join. `df.merge(df, on=[...], suffixes=("", "_teammate"))` pairs every row with every other row sharing the same race and constructor; `suffixes` controls how overlapping column names are disambiguated between the two copies.

**Deliberate difference from the SQL version:** Day 5's SQL used `f1.driver_key < f2.driver_key` specifically to produce *one* row per pairing (a head-to-head summary table). Here, `!=` is used instead of `<`, deliberately keeping **both directions** of each pairing — because this is a per-driver feature column (each driver needs their own row showing their personal delta relative to their teammate), not a summary table.

**Validation:** Pérez's `teammate_finish_delta` values against Verstappen were mostly negative across 2023, consistent with the 2–20 head-to-head record from Day 5. One notably extreme value (`-15` at round 6) checked out against real history — Monaco 2023, where Pérez crashed in qualifying and started last.

---

### Assembling the feature store

```python
feature_store = base_df.copy()
feature_store = compute_rolling_form(feature_store)
feature_store = compute_reliability_rate(feature_store)
feature_store = compute_grid_delta(feature_store)

teammate_features = compute_teammate_delta(base_df)[["driver_key", "race_key", "teammate_finish_delta"]]
feature_store = feature_store.merge(teammate_features, on=["driver_key", "race_key"], how="left")

feature_store.to_parquet("../data/processed/feature_store.parquet", index=False)
```
Three features chain directly onto the same DataFrame since they each add columns in place. The teammate feature is handled differently — since `compute_teammate_delta` performs its own internal self-merge and produces a differently-shaped result, only the one needed output column is extracted and joined back onto the main feature store via `driver_key` + `race_key`, the same conceptual operation as any SQL join, just performed in Pandas.

---

### Key lessons from Day 6
1. **Cross-validating a Pandas feature against an independently-written SQL query is a genuinely strong correctness check** — it caught a real bug (season-boundary bleed) that would have been easy to miss if the Pandas version had simply been trusted on its own.
2. **`.rolling()` vs `.expanding()`** are both legitimate but answer different questions — fixed recent-window trend vs. cumulative-since-start trend — worth choosing deliberately based on what the feature is meant to represent, not defaulting to one out of habit.
3. **`.transform()` vs `.apply()` on a groupby** — `.transform()` preserves the original row count/shape (one output per input row), which is required when adding a new column back onto the same DataFrame; `.apply()` can collapse groups, which is usually not what's wanted for row-level feature engineering.
4. **The same code can need different fixes in different execution contexts** (notebook vs. pytest) because each starts from a different working directory — solved generally with `pytest.ini`'s `pythonpath = .` rather than per-file path patching.
5. **Translating the same business logic (status categorization) identically across SQL and Python** is what makes a cross-tool validation meaningful — if the category rules had silently diverged between the two versions, any mismatch found would be a false signal, not a real bug.

### New concepts learned (added to running glossary)
- **`.groupby(...).transform(lambda ...)`** — applies a function per group while preserving the original row count/shape, unlike `.apply()`, which can collapse groups.
- **`.rolling(window=n, min_periods=1)`** — Pandas' fixed-size sliding-window calculation; `min_periods=1` allows partial windows at the start of a group (Pandas' equivalent of SQL's automatic partial-frame behavior).
- **`.expanding(min_periods=1)`** — a cumulative, ever-growing window from the start of a group, distinct from `.rolling()`'s fixed size.
- **`.cumcount()`** — numbers rows within each group starting at 0, useful for "how many records into this group so far."
- **`.cumsum()`** — running total within each group.
- **Boolean-to-flag pattern (`(condition).astype(int)`)** — converts a True/False Series into summable/averageable 1/0 values.
- **Self-merge (`df.merge(df, on=[...], suffixes=(...))`)** — the Pandas equivalent of a SQL self-join, pairing every row with every other row sharing specified key columns.
- **`.groupby(col).tail(1)`** vs **`.tail(n)`** — the former gets the last row of *each group*; the latter gets the last N rows of the whole (possibly multi-group) DataFrame — an easy trap when data isn't sorted the way it's assumed to be.
- **`pytest.ini` (`pythonpath = .`)** — tells pytest to add the project root to the import search path, independent of which subfolder tests are invoked from.

## Day 7 — Designing the Tableau Extract, Data Layering, and KPI Planning

### The core question this day answers
Days 1–6 built a correct, queryable, feature-rich warehouse — but Tableau Public cannot connect live to a local PostgreSQL database at all (no live external DB connections are permitted on Tableau Public, for security reasons). Day 7's job: design a denormalized, flattened data layer and export it into a `.hyper` file — the actual binary format Tableau reads — before any dashboard building begins on Day 8.

---

### KPI planning before touching any code

Wrote `docs/kpi_definitions.md` first, defining exactly what each of the three planned dashboards needs to show, before writing any SQL or export code:
- **Dashboard 1 — Executive Championship Overview:** cumulative points per driver per season, wins/podiums per constructor, current leader and points gap.
- **Dashboard 2 — Constructor Reliability Deep-Dive:** mechanical failure rate, finish rate, accident rate per constructor per season.
- **Dashboard 3 — Qualifying vs Race Pace:** grid vs finish position scatter, grid delta distribution, teammate head-to-head.

**Why plan this first:** avoids ending up with "a dashboard full of numbers that exist" rather than numbers that actually answer a real question — the KPI list becomes the source of truth Day 8's dashboards are built against.

---

### Designing a denormalized BI view

Real architectural principle applied here: **Tableau performs best against one flat, wide table with human-readable columns — not several normalized tables joined live inside Tableau itself.** The warehouse's normalized structure (5 dimensions, 2 facts, surrogate keys) is correct for a database, but wrong for a BI extract — so a SQL view was built specifically to flatten it.

```sql
CREATE VIEW vw_tableau_main AS
SELECT
    f.result_id,
    d.forename || ' ' || d.surname AS driver_name,
    d.nationality AS driver_nationality,
    c.name AS constructor_name,
    c.nationality AS constructor_nationality,
    ci.name AS circuit_name,
    ci.country AS circuit_country,
    r.year, r.round, r.race_date, r.name AS race_name,
    f.grid, f.position_order AS finish_position, f.points, f.laps,
    s.status,
    CASE
        WHEN s.status = 'Finished' OR s.status LIKE '+%Lap%' THEN 'Finished'
        WHEN s.status IN ('Accident', 'Collision', 'Spun off', 'Collision damage') THEN 'Accident'
        ELSE 'Mechanical/Other'
    END AS status_category,
    CASE WHEN f.grid > 0 THEN (f.grid - f.position_order) ELSE NULL END AS grid_delta
FROM fact_race_results f
JOIN dim_driver d ON f.driver_key = d.driver_key
JOIN dim_constructor c ON f.constructor_key = c.constructor_key
JOIN dim_race r ON f.race_key = r.race_key
JOIN dim_circuit ci ON r.circuit_key = ci.circuit_key
JOIN dim_status s ON f.status_key = s.status_key;
```

**Key concepts:**
- **`CREATE VIEW` vs `CREATE TABLE`** — a view stores no data itself; it re-runs its underlying query every time it's referenced, giving an always-current flattened representation of the warehouse without duplicating storage.
- **`d.forename || ' ' || d.surname AS driver_name`** — human-readable names substituted for surrogate keys, the essence of "denormalizing for BI": Tableau users shouldn't need to understand `driver_key = 847`, they need "Lewis Hamilton."
- **Every dimension joined into one flat row** — combines what Day 5's separate analytical queries each did individually into a single wide result Tableau can consume without needing to understand the relational structure at all.
- **`status_category`** reuses the Day 5/6 categorization logic directly inside the view, so Tableau's own calculated-field syntax doesn't need to reimplement it a third time.

---

### Bug 1: silent row loss from a `WHERE` clause that didn't do what it appeared to

**What happened:** the initial `.hyper` extract contained **25,121 rows**, not the expected 26,759 (the known `fact_race_results` row count from Day 4) — a gap of 1,638 missing rows, only caught because the row count was explicitly re-verified after export rather than assumed correct just because the file existed.

**Root cause:** the view's original filter,
```sql
WHERE f.grid > 0 OR f.grid IS NULL
```
was intended to mean "keep every row except invalid pit-lane starts." But the `grid` column stores "no grid position" as the literal integer `0`, not a true SQL `NULL` — meaning `f.grid IS NULL` was essentially always false, and the condition silently collapsed to just `WHERE f.grid > 0`, quietly dropping every pit-lane-start row from the *entire* extract — not just from grid-delta-specific calculations where that exclusion would have been appropriate.

**Deeper design issue exposed:** this wasn't just a syntax mistake — it revealed that a single wide view was trying to simultaneously serve dashboards with genuinely different filtering needs. Excluding grid=0 rows is correct for Dashboard 3 (qualifying vs. race pace, where an invalid grid position breaks the calculation), but wrong for Dashboards 1–2 (championship points, reliability rate), which need every race entry regardless of starting grid.

**Fix:** removed the row-excluding `WHERE` clause entirely, keeping every row in the view. Moved the grid-validity check down into the `grid_delta` column itself, so invalid rows get a `NULL` in that one column instead of being dropped from the table altogether:
```sql
CASE WHEN f.grid > 0 THEN (f.grid - f.position_order) ELSE NULL END AS grid_delta
```
This lets Tableau's own filters decide, per-chart, whether to exclude null `grid_delta` values — appropriate for Dashboard 3, irrelevant for Dashboards 1–2, which now correctly retain every row.

**Result:** view row count returned to 26,759, matching the warehouse exactly.

---

### Building the `.hyper` export pipeline

Installed `tableauhyperapi` and wrote `src/tableau_export.py`, using Tableau's own Python library to write a native `.hyper` file — the actual binary format Tableau Desktop/Public read.

```python
def export_to_hyper():
    df = pd.read_sql("SELECT * FROM vw_tableau_main", engine)

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=OUTPUT_PATH,
                         create_mode=CreateMode.CREATE_AND_REPLACE) as connection:

            table_def = TableDefinition(
                table_name=TableName("Extract", "f1_results"),
                columns=[
                    TableDefinition.Column("result_id", SqlType.int()),
                    TableDefinition.Column("driver_name", SqlType.text()),
                    # ... one Column per SELECT column, each explicitly typed
                ]
            )

            connection.catalog.create_schema("Extract")
            connection.catalog.create_table(table_def)

            with Inserter(connection, table_def) as inserter:
                inserter.add_rows(rows=rows)
                inserter.execute()
```

**Key concepts:**
- **`HyperProcess`** — starts a temporary local background process running Tableau's own "Hyper" database engine, which knows how to write `.hyper` files directly.
- **`TableDefinition(...)`** — Hyper files require an explicit schema declared up front, conceptually identical to Day 3's DDL, just expressed through the Hyper API's Python interface and its own type system (`SqlType.int()`, `SqlType.text()`, `SqlType.date()`, `SqlType.double()`) rather than raw SQL.
- **`Inserter(...).add_rows(...).execute()`** — the bulk-write mechanism, taking prepared rows and writing them into the `.hyper` file in one batch operation.

---

### Bug 2: `TypeError`/`ValueError` from a Pandas float/int mismatch, persisting across multiple fix attempts

**What happened:** after fixing Bug 1 (allowing `grid_delta` to hold `NULL`), the export began failing with:
```
ValueError: Got an invalid value 0.0 for column "grid_delta", it must be an int instance
```

**Root cause:** once `grid_delta` could contain both whole numbers *and* nulls, Pandas silently upcast the entire column from an integer dtype to a **float** dtype — because Pandas' base integer type has no way to represent a missing value, so any integer column containing at least one null gets automatically converted to float. This meant a conceptually-integer value like `0` was actually being stored and passed to the Hyper API as the float `0.0`. The `TableDefinition` had declared `grid_delta` as strict `SqlType.int()`, so the Hyper API correctly rejected the float.

**First fix attempt (insufficient):** converting just the `grid_delta` column to Python `int`/`None` via `.apply()`, run immediately before a separate DataFrame-wide line:
```python
df = df.astype(object).where(pd.notnull(df), None)
```
This still failed, with the *identical* error, across several retries — including after a full file rewrite and a hard notebook restart, which ruled out stale code/caching as the cause.

**Diagnosing it properly:** rather than keep patching blindly, ran the export directly via `python -m src.tableau_export` from the terminal — deliberately removing the notebook/autoreload environment as a possible variable. The identical error still occurred, proving the bug was genuinely in the code's logic, not in notebook state.

**Actual root cause identified:** the DataFrame-wide line `df.astype(object).where(pd.notnull(df), None)`, which ran *after* the per-column integer fix, was re-touching every column across the whole table — including the one already correctly converted — and Pandas' internal type re-inference during that whole-frame operation was silently reintroducing float representations for values that had just been correctly set as integers moments earlier. A per-column fix was being undone by a later DataFrame-wide operation.

**Final fix — explicit per-value conversion, avoiding all DataFrame-wide dtype operations entirely:**
```python
COLUMN_TYPES = {
    "result_id": "int", "grid_delta": "int", "points": "double",
    "race_date": "date", "driver_name": "text",
    # ... one entry per column, mapped to its Hyper type
}

def convert_value(value, col_type: str):
    if pd.isna(value):
        return None
    if col_type == "int":
        return int(value)
    if col_type == "double":
        return float(value)
    if col_type == "date" and hasattr(value, "date"):
        return value.date()
    return value

def build_rows(df: pd.DataFrame) -> list:
    columns_order = list(COLUMN_TYPES.keys())
    rows = []
    for record in df[columns_order].itertuples(index=False, name=None):
        row = [convert_value(v, COLUMN_TYPES[col]) for v, col in zip(record, columns_order)]
        rows.append(row)
    return rows
```

**Key concepts:**
- **`pd.isna(value)` checked per-value, not per-DataFrame** — reliably catches `NaN`, `None`, and `NaT` (Pandas' null-date marker) uniformly, at the moment each individual value is handled, with no whole-table operation left to undo it afterward.
- **`.itertuples(index=False, name=None)`** — iterates a DataFrame row by row, yielding plain Python tuples of raw values, explicitly in a specified column order — avoiding both the overhead and the surprising type-inference behavior of DataFrame-wide dtype casting.
- **Trade-off accepted knowingly:** row-by-row Python conversion is slower than a vectorized Pandas operation, but for a one-time export step (not a tight performance-critical loop), predictability was judged more valuable than raw speed.

**Result:** export succeeded cleanly — `26,759` rows pulled, converted, and written without error. Re-verified by reopening the `.hyper` file independently and running `COUNT(*)` directly against it, confirming the row count matched the warehouse exactly.

---

### Key lessons from Day 7
1. **Tableau Public's extract-only connectivity model is a real, resume-worthy architectural constraint**, not an inconvenience to work around quietly — it directly shaped the decision to build a dedicated denormalized view and export pipeline rather than pointing Tableau at the warehouse directly.
2. **Never assume a `WHERE` clause behaves as intended without checking the data's actual null/placeholder conventions.** A column can represent "no value" using a sentinel value (`0`) rather than a true `NULL` — and a filter written assuming otherwise can fail silently, producing a plausible-looking but wrong row count.
3. **Pandas silently changes a column's dtype when nulls are introduced into what was previously a clean integer column** — a genuinely common, easy-to-miss source of downstream type errors in any tool (like the Hyper API) that enforces strict typing.
4. **DataFrame-wide dtype operations can silently undo an already-correct per-column fix.** When a targeted fix doesn't hold, the right response is to remove ambiguity entirely — explicit, per-value conversion — rather than keep patching the same DataFrame-wide operation repeatedly.
5. **Eliminating the notebook/autoreload environment as a variable (by running the exact same code via `python -m module` in the terminal) is a genuinely useful debugging technique** when an error persists identically across multiple supposed fixes — it separates "is my code actually wrong" from "is my execution environment stale," two very different problems that produce identical-looking symptoms.
6. **Verifying a pipeline's output by count, not just by "the file exists" or "the script didn't crash,"** caught a real 1,638-row discrepancy that would otherwise have silently undercounted every chart built from this extract on Day 8 — the same "verify, don't assume" discipline applied since Day 2's null-count checks, now applied to a binary Tableau file instead of a CSV.

### New concepts learned (added to running glossary)
- **`.hyper` file** — Tableau's native binary extract format, required for Tableau Public since it cannot maintain live external database connections.
- **`CREATE VIEW`** — a saved, reusable query that behaves like a virtual table, re-executing its definition on each reference rather than storing data itself.
- **Denormalization for BI** — deliberately flattening a normalized (star schema) structure into one wide table with human-readable values, since BI tools generally perform better and are easier to build against with fewer live joins.
- **Sentinel value vs. true `NULL`** — a placeholder value (like `0` meaning "no grid position") that represents missing/invalid data without being a genuine SQL `NULL` — filters checking `IS NULL` will not catch sentinel values, a common, easy-to-miss source of silent bugs.
- **Hyper API (`HyperProcess`, `TableDefinition`, `Inserter`)** — Tableau's official Python library for programmatically creating and writing `.hyper` extract files outside of the Tableau Desktop UI.
- **Integer column upcasting to float on null introduction** — a core Pandas behavior: a column of whole numbers automatically becomes a float dtype the moment any value in it becomes missing/null, since Pandas' base integer type cannot represent "no value."
- **DataFrame-wide vs. per-value type conversion** — whole-table operations like `.astype(object)` can silently re-infer and override types across every column, including ones already correctly fixed; explicit per-value conversion (via `.itertuples()` and a manual conversion function) avoids this ambiguity entirely.
- **Terminal execution as a debugging isolation technique** — running `python -m module_name` directly rules out notebook state/caching (autoreload staleness, leftover kernel variables) as the cause of a persistent bug, isolating whether the problem is in the code itself.