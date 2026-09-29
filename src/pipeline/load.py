"""Orchestration for the loading stage."""

from src.db.load_media import insert_article
from src.db.load_structured import load_structured_data


def load() -> dict[str, int]:
    """Load processed records and return validated row counts."""
    validated_counts = load_structured_data()
    validated_counts["metadata"] = insert_article()
    return validated_counts
