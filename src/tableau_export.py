import logging
from pathlib import Path

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


def export_to_hyper():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    import pandas as pd
    df = pd.read_sql("SELECT * FROM vw_tableau_main", engine)
    logger.info(f"Pulled {len(df)} rows from vw_tableau_main")

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

            df = df.astype(object).where(pd.notnull(df), None)

            with Inserter(connection, table_def) as inserter:
                inserter.add_rows(rows=df.values.tolist())
                inserter.execute()

    logger.info(f"Hyper extract written to {OUTPUT_PATH}")


if __name__ == "__main__":
    export_to_hyper()