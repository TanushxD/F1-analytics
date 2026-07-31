import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

import kagglehub
import pandas as pd

from src.config import RAW_DATA_DIR, KAGGLE_DATASET

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def download_dataset() -> Path:
    logger.info(f"Downloading dataset: {KAGGLE_DATASET}")
    path = kagglehub.dataset_download(KAGGLE_DATASET)
    logger.info(f"Dataset cached at: {path}")
    return Path(path)


def copy_to_raw(source_path: Path) -> list[Path]:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    copied_files = []

    for csv_file in source_path.glob("*.csv"):
        destination = RAW_DATA_DIR / csv_file.name
        shutil.copy2(csv_file, destination)
        copied_files.append(destination)
        logger.info(f"Copied {csv_file.name} -> {destination}")

    return copied_files


def build_manifest(files: list[Path]) -> None:
    manifest = {
        "download_timestamp": datetime.now().isoformat(),
        "dataset": KAGGLE_DATASET,
        "files": []
    }

    for file_path in files:
        df = pd.read_csv(file_path)
        manifest["files"].append({
            "filename": file_path.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_kb": round(file_path.stat().st_size / 1024, 2)
        })

    manifest_path = RAW_DATA_DIR / "_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to {manifest_path}")


def run_extraction():
    source_path = download_dataset()
    copied_files = copy_to_raw(source_path)
    build_manifest(copied_files)
    logger.info("Extraction complete.")


if __name__ == "__main__":
    run_extraction()