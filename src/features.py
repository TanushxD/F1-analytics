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