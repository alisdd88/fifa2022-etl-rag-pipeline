"""Shared logging configuration."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure a readable default log format for command-line runs."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
