import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

import kagglehub
import pandas as pd

from src.config import RAW_CAREER_DIR, RAW_RACES_DIR, KAGGLE_DATASET_CAREER, KAGGLE_DATASET_RACES

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def download_dataset(dataset_handle: str) -> Path:
    """Downloads a given Kaggle dataset and returns its local cache path."""
    logger.info(f"Downloading dataset: {dataset_handle}")
    path = kagglehub.dataset_download(dataset_handle)
    logger.info(f"Dataset cached at: {path}")
    return Path(path)


def copy_to_raw(source_path: Path, destination_dir: Path) -> list[Path]:
    """Copies all CSV files from a kagglehub cache folder into our project's raw data folder."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    copied_files = []

    for csv_file in source_path.glob("*.csv"):
        destination = destination_dir / csv_file.name
        shutil.copy2(csv_file, destination)
        copied_files.append(destination)
        logger.info(f"Copied {csv_file.name} -> {destination}")

    return copied_files


def build_manifest(files: list[Path], destination_dir: Path, dataset_handle: str) -> None:
    """Logs row counts, column counts, and file sizes for every extracted file."""
    manifest = {
        "download_timestamp": datetime.now().isoformat(),
        "dataset": dataset_handle,
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

    manifest_path = destination_dir / "_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to {manifest_path}")


def run_extraction():
    # Dataset 1: career-level driver stats (already downloaded, safe to re-run)
    career_source = download_dataset(KAGGLE_DATASET_CAREER)
    career_files = copy_to_raw(career_source, RAW_CAREER_DIR)
    build_manifest(career_files, RAW_CAREER_DIR, KAGGLE_DATASET_CAREER)

    # Dataset 2: race-by-race relational history (new)
    races_source = download_dataset(KAGGLE_DATASET_RACES)
    races_files = copy_to_raw(races_source, RAW_RACES_DIR)
    build_manifest(races_files, RAW_RACES_DIR, KAGGLE_DATASET_RACES)

    logger.info("Extraction complete for both datasets.")


if __name__ == "__main__":
    run_extraction()