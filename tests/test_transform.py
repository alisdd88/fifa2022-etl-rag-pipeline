"""Tests for transformation-stage orchestration."""

from unittest.mock import patch

from src.etl.pipeline.transform import transform


def test_transform_runs_statsbomb_then_article_preprocessing() -> None:
    """The transformation stage runs both approved preprocessing operations."""
    stage_calls = []

    with (
        patch(
            "src.etl.pipeline.transform.normalize_statsbomb",
            side_effect=lambda: stage_calls.append("statsbomb"),
        ),
        patch(
            "src.etl.pipeline.transform.transform_articles",
            side_effect=lambda: stage_calls.append("articles"),
        ),
    ):
        transform()

    assert stage_calls == ["statsbomb", "articles"]
