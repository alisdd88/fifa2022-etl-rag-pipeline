"""Tests for database loading orchestration."""

from unittest.mock import patch

from src.pipeline.load import load


def test_load_returns_validated_structured_counts() -> None:
    """The load stage returns the structured loader's validation result."""
    expected_counts = {
        "competition": 1,
        "matches": 3,
        "lineups": 147,
        "events": 84,
    }

    with patch(
        "src.pipeline.load.load_structured_data",
        return_value=expected_counts,
    ) as structured_loader:
        result = load()

    structured_loader.assert_called_once_with()
    assert result == expected_counts
