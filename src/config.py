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

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"