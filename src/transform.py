import pandas as pd
import numpy as np


def clean_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Replaces literal '\\N' strings and empty strings with real NaN values."""
    df = df.replace(r'^\s*\\N\s*$', np.nan, regex=True)
    df = df.replace(r'^\s*$', np.nan, regex=True)
    return df


def parse_lap_time(time_str) -> float:
    """Converts a lap time string like '1:23.456' into total milliseconds.
    Returns NaN if the input is missing or unparseable."""
    if pd.isna(time_str):
        return np.nan

    time_str = str(time_str).strip()

    if time_str in ("", "\\N"):
        return np.nan

    try:
        if ":" in time_str:
            minutes_part, seconds_part = time_str.split(":")
            minutes = int(minutes_part)
            seconds = float(seconds_part)
            total_ms = (minutes * 60 + seconds) * 1000
        else:
            total_ms = float(time_str) * 1000

        return round(total_ms)

    except (ValueError, TypeError):
        return np.nan