import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_CAREER_DIR = RAW_DATA_DIR / "career_stats"
RAW_RACES_DIR = RAW_DATA_DIR / "race_history"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

KAGGLE_DATASET_CAREER = "kushagrajain19/f1-drivers-dataset-1950-2026"
KAGGLE_DATASET_RACES = "rohanrao/formula-1-world-championship-1950-2020"