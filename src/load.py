import logging
import pandas as pd

from src.db import engine
from src.config import PROCESSED_DATA_DIR
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RACE_HISTORY_DIR = PROCESSED_DATA_DIR / "race_history"


def load_dim_driver():
    df = pd.read_parquet(RACE_HISTORY_DIR / "drivers.parquet")
    df = df.rename(columns={
        "driverId": "driver_id",
        "driverRef": "driver_ref",
    })
    df = df[["driver_id", "driver_ref", "code", "forename", "surname", "dob", "nationality"]]
    df.to_sql("dim_driver", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_driver")


def load_dim_constructor():
    df = pd.read_parquet(RACE_HISTORY_DIR / "constructors.parquet")
    df = df.rename(columns={
        "constructorId": "constructor_id",
        "constructorRef": "constructor_ref",
    })
    df = df[["constructor_id", "constructor_ref", "name", "nationality"]]
    df.to_sql("dim_constructor", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_constructor")


def load_dim_circuit():
    df = pd.read_parquet(RACE_HISTORY_DIR / "circuits.parquet")
    df = df.rename(columns={
        "circuitId": "circuit_id",
        "circuitRef": "circuit_ref",
    })
    df = df[["circuit_id", "circuit_ref", "name", "location", "country", "lat", "lng", "alt"]]
    df.to_sql("dim_circuit", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_circuit")


def load_dim_status():
    df = pd.read_parquet(RACE_HISTORY_DIR / "status.parquet")
    df = df.rename(columns={"statusId": "status_id"})
    df = df[["status_id", "status"]]
    df.to_sql("dim_status", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_status")


def get_key_mapping(table_name: str, natural_col: str, surrogate_col: str) -> dict:
    """Reads a dimension table back out and builds a {natural_id: surrogate_key} lookup dict."""
    query = f"SELECT {natural_col}, {surrogate_col} FROM {table_name}"
    df = pd.read_sql(query, engine)
    return dict(zip(df[natural_col], df[surrogate_col]))


def load_dim_race():
    circuit_mapping = get_key_mapping("dim_circuit", "circuit_id", "circuit_key")

    df = pd.read_parquet(RACE_HISTORY_DIR / "races.parquet")
    df = df.rename(columns={
        "raceId": "race_id",
        "circuitId": "circuit_id",
        "date": "race_date",
    })
    df["circuit_key"] = df["circuit_id"].map(circuit_mapping)
    df = df[["race_id", "circuit_key", "year", "round", "name", "race_date"]]
    df.to_sql("dim_race", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into dim_race")

from src.transform import clean_nulls, parse_lap_time


def load_fact_race_results():
    driver_map = get_key_mapping("dim_driver", "driver_id", "driver_key")
    constructor_map = get_key_mapping("dim_constructor", "constructor_id", "constructor_key")
    race_map = get_key_mapping("dim_race", "race_id", "race_key")
    status_map = get_key_mapping("dim_status", "status_id", "status_key")

    df = pd.read_parquet(RACE_HISTORY_DIR / "results.parquet")

    df = df.rename(columns={
        "resultId": "result_id",
        "positionOrder": "position_order",
        "time": "time_text",
        "fastestLap": "fastest_lap",
        "fastestLapTime": "fastest_lap_time_text",
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
    logger.info(f"Loaded {len(df)} rows into fact_race_results")


def load_fact_qualifying():
    driver_map = get_key_mapping("dim_driver", "driver_id", "driver_key")
    constructor_map = get_key_mapping("dim_constructor", "constructor_id", "constructor_key")
    race_map = get_key_mapping("dim_race", "race_id", "race_key")

    df = pd.read_parquet(RACE_HISTORY_DIR / "qualifying.parquet")

    df = df.rename(columns={
        "qualifyId": "qualify_id",
        "q1": "q1_text",
        "q2": "q2_text",
        "q3": "q3_text",
    })

    df["q1_ms"] = df["q1_text"].apply(parse_lap_time)
    df["q2_ms"] = df["q2_text"].apply(parse_lap_time)
    df["q3_ms"] = df["q3_text"].apply(parse_lap_time)

    df["driver_key"] = df["driverId"].map(driver_map)
    df["constructor_key"] = df["constructorId"].map(constructor_map)
    df["race_key"] = df["raceId"].map(race_map)

    rows_before = len(df)
    df = df.dropna(subset=["driver_key", "constructor_key", "race_key"])
    rows_after = len(df)
    if rows_before != rows_after:
        logger.warning(f"Dropped {rows_before - rows_after} rows with unmatched keys in fact_qualifying")

    df = df[[
        "qualify_id", "race_key", "driver_key", "constructor_key",
        "position", "q1_text", "q2_text", "q3_text", "q1_ms", "q2_ms", "q3_ms"
    ]]

    df.to_sql("fact_qualifying", engine, if_exists="append", index=False)
    logger.info(f"Loaded {len(df)} rows into fact_qualifying")

def reset_tables():
    """Clears all warehouse tables (in dependency order) so the load is safe to re-run from scratch."""
    tables_in_dependency_order = [
        "fact_qualifying",
        "fact_race_results",
        "dim_race",
        "dim_status",
        "dim_circuit",
        "dim_constructor",
        "dim_driver",
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
    logger.info("All dimension tables loaded.")

    load_fact_race_results()
    load_fact_qualifying()
    logger.info("All fact tables loaded.")