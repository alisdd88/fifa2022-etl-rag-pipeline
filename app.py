"""Command-line entry point for the project."""

from src.etl.pipeline.etl import run_etl
from src.etl.utils.logging import configure_logging


def main() -> None:
    """Configure logging and run the ETL pipeline."""
    configure_logging()
    run_etl()


if __name__ == "__main__":
    main()
