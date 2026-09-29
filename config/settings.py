"""Central project paths and conservative acquisition defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHROMA_DB_DIR = PROCESSED_DATA_DIR / "chroma"
METADATA_DIR = DATA_DIR / "metadata"
DATABASE_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = "all-MiniLM-L6-v2"
RAG_COLLECTION_NAME = "articles"
RAG_DISTANCE_METRIC = "cosine"
RAG_INDEX_SCHEMA_VERSION = 1

# Limits selected for the curated project scope.
ARTICLE_LIMIT = 3
CHUNK_SIZE = 300
CHUNK_OVERLAP = 15
IMAGE_LIMIT: int | None = None
