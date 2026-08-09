import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_results_base(engine) -> pd.DataFrame:
    """Pulls a clean, joined driver-result-race base table straight from the warehouse."""
    query = """
        SELECT
            f.result_id,
            d.driver_key,
            d.forename,
            d.surname,
            c.constructor_key,
            c.name AS constructor_name,
            r.race_key,
            r.year,
            r.round,
            r.race_date,
            f.grid,
            f.position_order,
            f.points,
            s.status
        FROM fact_race_results f
        JOIN dim_driver d ON f.driver_key = d.driver_key
        JOIN dim_constructor c ON f.constructor_key = c.constructor_key
        JOIN dim_race r ON f.race_key = r.race_key
        JOIN dim_status s ON f.status_key = s.status_key
        ORDER BY d.driver_key, r.race_date
    """
    return pd.read_sql(query, engine)

def compute_rolling_form(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Computes a trailing rolling average of points per driver, resetting at each season
    boundary (matches Day 5's SQL definition of 'form within a season'). Uses only past
    races within that season — no lookahead bias, no cross-season bleed.
    """
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()

    df["rolling_form_index"] = (
        df.groupby(["driver_key", "year"])["points"]
        .transform(lambda x: x.rolling(window=window, min_periods=1).mean())
    )

    return df

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
    """
    Computes each driver's cumulative (season-to-date) reliability rate: the share of
    races finished (not mechanically failed) up to and including each race, using only
    past results within that season — no lookahead bias.
    """
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()

    df["status_category"] = df["status"].apply(categorize_status)
    df["is_finished"] = (df["status_category"] == "Finished").astype(int)

    df["races_so_far"] = df.groupby(["driver_key", "year"]).cumcount() + 1
    df["finishes_so_far"] = (
        df.groupby(["driver_key", "year"])["is_finished"].cumsum()
    )

    df["reliability_rate"] = round(
        df["finishes_so_far"] / df["races_so_far"] * 100, 1
    )

    return df

def compute_grid_delta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes per-race grid-to-finish delta, plus a running (expanding) average that
    shows how a driver's overtaking ability trends over the course of a season —
    using only past races at each point, no lookahead bias.
    """
    df = df.sort_values(["driver_key", "year", "race_date"]).copy()

    df["grid_delta"] = df["grid"] - df["position_order"]

    valid_grid = df["grid"] > 0
    df.loc[valid_grid, "grid_delta_running_avg"] = (
        df[valid_grid]
        .groupby(["driver_key", "year"])["grid_delta"]
        .transform(lambda x: x.expanding(min_periods=1).mean())
    )

    return df

def compute_teammate_delta(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each race, computes each driver's finishing position relative to their teammate
    (same constructor, same race). Positive means the driver beat their teammate.
    """
    merged = df.merge(
        df,
        on=["race_key", "constructor_key"],
        suffixes=("", "_teammate")
    )

    merged = merged[merged["driver_key"] != merged["driver_key_teammate"]]

    merged["teammate_finish_delta"] = (
        merged["position_order_teammate"] - merged["position_order"]
    )

    result = merged[[
        "driver_key", "race_key", "year", "round", "forename", "surname",
        "constructor_name", "position_order", "driver_key_teammate",
        "position_order_teammate", "teammate_finish_delta"
    ]]

    return result