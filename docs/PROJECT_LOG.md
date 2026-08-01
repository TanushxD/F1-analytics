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

## What's Next — Day 3

Designing the Star Schema data warehouse: identifying the fact table grain (one driver's result in one race), building dimension tables (driver, constructor, circuit, race, status), and standing up the target database (PostgreSQL or DuckDB).