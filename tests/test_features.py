import pandas as pd
import sys, os

sys.path.append(os.path.abspath(".."))
from src.features import compute_rolling_form


def test_rolling_form_no_lookahead_bias():
    """A driver's rolling form at any race must only reflect races up to and including
    that race — never a future race's points."""
    sample_data = pd.DataFrame({
        "driver_key": [1, 1, 1, 1, 1],
        "year": [2023, 2023, 2023, 2023, 2023],
        "race_date": pd.to_datetime([
            "2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01", "2023-05-01"
        ]),
        "points": [10, 20, 30, 40, 50],
    })

    result = compute_rolling_form(sample_data, window=3)

    expected = [10.0, 15.0, 20.0, 30.0, 40.0]

    for i, exp_value in enumerate(expected):
        actual_value = result.iloc[i]["rolling_form_index"]
        assert abs(actual_value - exp_value) < 0.001, (
            f"Row {i}: expected {exp_value}, got {actual_value}"
        )


def test_rolling_form_resets_per_season():
    """Rolling form must reset at season boundaries, not bleed across years."""
    sample_data = pd.DataFrame({
        "driver_key": [1, 1, 1],
        "year": [2022, 2023, 2023],
        "race_date": pd.to_datetime(["2022-11-01", "2023-01-01", "2023-02-01"]),
        "points": [100, 10, 20],
    })

    result = compute_rolling_form(sample_data, window=5)

    row_2023_first = result[(result["year"] == 2023)].iloc[0]
    assert row_2023_first["rolling_form_index"] == 10.0, (
        "First 2023 race's rolling form should not include 2022's 100 points"
    )