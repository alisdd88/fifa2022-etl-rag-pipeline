"""Orchestration for the transformation stage."""

from src.preprocessing.statsbomb import normalize_statsbomb


def transform() -> None:
    """Run the approved modality-specific preprocessing operations."""
    # Transform structured StatsBomb data into processed tables.
    normalize_statsbomb()
