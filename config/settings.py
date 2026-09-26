"""Central project paths and conservative acquisition defaults."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
DATABASE_PATH = PROCESSED_DATA_DIR / "fifa2022.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# Limits must be selected after the data-availability audit.
ARTICLE_LIMIT: int | None = None
IMAGE_LIMIT: int | None = None
