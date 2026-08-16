# Known Issues / Open Bugs

Lightweight issue tracker for bugs found but not yet resolved — reviewed and closed out as they're fixed.

---

## OPEN

### #1 — KPI "Season Leader" tile shows wrong driver for 2024

**Status:** Open — diagnosis in progress
**Found:** Day 8, while building the Executive Summary KPI tiles
**Severity:** High — this is a headline/BAN-tile number, likely to be one of the first things a viewer sees

**Symptom:**
`KPI - Season Leader` worksheet, filtered to Year = 2024, Top-1-by-`SUM(Points)` on `Driver Name`, displays **"Lewis Hamilton"**. This is factually wrong — Hamilton finished 7th in the real 2024 F1 World Championship.

**Confirmed via direct SQL against the warehouse (ground truth, verified correct):**
```sql
SELECT d.forename, d.surname, SUM(f.points) as total_points
FROM fact_race_results f
JOIN dim_driver d ON f.driver_key = d.driver_key
JOIN dim_race r ON f.race_key = r.race_key
WHERE r.year = 2024
GROUP BY d.forename, d.surname
ORDER BY total_points DESC
LIMIT 5;
```
Result:
```
Max Verstappen   399.0
Lando Norris     344.0
Charles Leclerc  327.0
Oscar Piastri    265.0
Carlos Sainz     262.0
```
This confirms the **warehouse data is correct** — the bug is isolated to the Tableau worksheet's configuration, not the underlying data or pipeline.

**Leading hypothesis:**
The `KPI - Season Leader` worksheet was likely created via "Duplicate Sheet" from the earlier `Qualifying vs Race Pace` scatter plot sheet, which had a **manual `Driver Name` filter** restricted to 5 specific drivers (Leclerc, Alonso, Norris, Hamilton, Verstappen). That old filter may still be active underneath/alongside the new Top-1-by-points filter — meaning Tableau could be computing "Top 1 among only these 5 pre-selected drivers" rather than the full driver pool, and something about how that resolves (sort direction? stale filter state?) is landing on Hamilton instead of Verstappen.

**Next steps to diagnose (pick up here):**
1. Click the `Driver Name` pill on the Filters shelf of the `KPI - Season Leader` sheet.
2. Check every tab of that filter dialog (General / Wildcard / Condition / Top) — screenshot each.
3. If a manual driver list (General tab) is checked alongside the Top-1 condition, remove the manual list entirely — keep only the Top-1-by-`SUM(Points)` condition.
4. Also double check the `Year` filter on this same sheet is genuinely locked to 2024, not left on 2023 or "All."
5. Re-verify the tile displays "Verstappen" after the fix.
6. **Going forward:** build new worksheets from scratch (right-click → New Worksheet) rather than duplicating an existing one with unrelated filters already applied, to avoid this class of bug recurring on future tiles (Total Races, Points Gap).

---

## RESOLVED

*(Bugs get moved here once fixed, with a one-line summary + link to the relevant PROJECT_LOG.md day for the full writeup.)*

- `\N` null handling in raw CSVs — Day 2, see `docs/PROJECT_LOG.md`
- Season-boundary bleed in rolling form index — Day 6
- WHERE clause silently dropping grid=0 rows in Tableau extract view — Day 7
- Pandas float/int mismatch breaking Hyper API insert — Day 7
- Tableau Public unable to open `.hyper` files directly — Day 8
- Scatter plot over-aggregation (Aggregate Measures toggle) — Day 8