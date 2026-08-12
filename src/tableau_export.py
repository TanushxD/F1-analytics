import logging
from pathlib import Path

import pandas as pd
from tableauhyperapi import (
    HyperProcess, Telemetry, Connection, CreateMode,
    TableDefinition, SqlType, TableName, Inserter
)

from src.db import engine
from src.config import PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "dashboards" / "tableau"
OUTPUT_PATH = OUTPUT_DIR / "f1_main_extract.hyper"

# Column name -> its Hyper type, used to explicitly convert every value
# at insert time rather than relying on DataFrame-wide dtype casting.
COLUMN_TYPES = {
    "result_id": "int",
    "driver_name": "text",
    "driver_nationality": "text",
    "constructor_name": "text",
    "constructor_nationality": "text",
    "circuit_name": "text",
    "circuit_country": "text",
    "year": "int",
    "round": "int",
    "race_date": "date",
    "race_name": "text",
    "grid": "int",
    "finish_position": "int",
    "points": "double",
    "laps": "int",
    "status": "text",
    "status_category": "text",
    "grid_delta": "int",
}


def convert_value(value, col_type: str):
    """Converts a single raw value to the exact Python type the Hyper API expects."""
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
    """Converts every row of the DataFrame into a list of correctly-typed values,
    column by column, value by value — explicit and safe, avoiding Pandas'
    automatic (and sometimes surprising) dtype inference at the DataFrame level."""
    columns_order = list(COLUMN_TYPES.keys())
    rows = []
    for record in df[columns_order].itertuples(index=False, name=None):
        row = [convert_value(v, COLUMN_TYPES[col]) for v, col in zip(record, columns_order)]
        rows.append(row)
    return rows


def export_to_hyper():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_sql("SELECT * FROM vw_tableau_main", engine)
    logger.info(f"Pulled {len(df)} rows from vw_tableau_main")

    rows = build_rows(df)
    logger.info(f"Converted {len(rows)} rows to Hyper-compatible types")

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(
            endpoint=hyper.endpoint,
            database=OUTPUT_PATH,
            create_mode=CreateMode.CREATE_AND_REPLACE
        ) as connection:

            table_def = TableDefinition(
                table_name=TableName("Extract", "f1_results"),
                columns=[
                    TableDefinition.Column("result_id", SqlType.int()),
                    TableDefinition.Column("driver_name", SqlType.text()),
                    TableDefinition.Column("driver_nationality", SqlType.text()),
                    TableDefinition.Column("constructor_name", SqlType.text()),
                    TableDefinition.Column("constructor_nationality", SqlType.text()),
                    TableDefinition.Column("circuit_name", SqlType.text()),
                    TableDefinition.Column("circuit_country", SqlType.text()),
                    TableDefinition.Column("year", SqlType.int()),
                    TableDefinition.Column("round", SqlType.int()),
                    TableDefinition.Column("race_date", SqlType.date()),
                    TableDefinition.Column("race_name", SqlType.text()),
                    TableDefinition.Column("grid", SqlType.int()),
                    TableDefinition.Column("finish_position", SqlType.int()),
                    TableDefinition.Column("points", SqlType.double()),
                    TableDefinition.Column("laps", SqlType.int()),
                    TableDefinition.Column("status", SqlType.text()),
                    TableDefinition.Column("status_category", SqlType.text()),
                    TableDefinition.Column("grid_delta", SqlType.int()),
                ]
            )

            connection.catalog.create_schema("Extract")
            connection.catalog.create_table(table_def)

            with Inserter(connection, table_def) as inserter:
                inserter.add_rows(rows=rows)
                inserter.execute()

    logger.info(f"Hyper extract written to {OUTPUT_PATH}")


if __name__ == "__main__":
    export_to_hyper()