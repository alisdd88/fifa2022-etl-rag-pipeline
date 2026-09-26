"""Top-level ETL orchestration."""

from src.pipeline.extract import extract
from src.pipeline.load import load
from src.pipeline.transform import transform


def run_etl() -> None:
    """Run extraction, transformation, and loading in sequence."""
    extract()
    transform()
    load()
