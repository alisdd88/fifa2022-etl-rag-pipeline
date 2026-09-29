"""Tests for database loading orchestration."""

from unittest.mock import patch

from src.pipeline.load import load


def test_load_returns_validated_structured_and_article_counts() -> None:
    """The load stage runs structured loading before article metadata loading."""
    structured_counts = {
        "competition": 1,
        "matches": 3,
        "lineups": 147,
        "events": 84,
    }

    with (
        patch(
            "src.pipeline.load.load_structured_data",
            return_value=structured_counts,
        ) as structured_loader,
        patch("src.pipeline.load.insert_article", return_value=8) as article_loader,
    ):
        result = load()

    structured_loader.assert_called_once_with()
    article_loader.assert_called_once_with()
    assert result == {**structured_counts, "metadata": 8}
