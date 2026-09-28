"""Orchestration for the loading stage."""

from src.db.load_structured import load_structured_data


def load() -> dict[str, int]:
    """Load processed structured records and return validated row counts."""
    return load_structured_data()
