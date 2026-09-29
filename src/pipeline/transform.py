"""Orchestration for the transformation stage."""

from src.preprocessing.articles import transform_articles
from src.preprocessing.statsbomb import normalize_statsbomb


def transform() -> None:
    """Run the approved modality-specific preprocessing operations."""
    # Transform structured StatsBomb data into processed tables.
    normalize_statsbomb()

    # Transform manually approved Guardian articles into text and metadata.
    transform_articles()
