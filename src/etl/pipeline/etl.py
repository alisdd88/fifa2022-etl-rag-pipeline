"""Top-level ETL orchestration."""

from src.etl.pipeline.extract import extract
from src.etl.pipeline.load import load
from src.etl.pipeline.transform import transform


def run_etl() -> None:
    """Run extraction, transformation, and loading in sequence."""
    extract()
    transform()
    load()
