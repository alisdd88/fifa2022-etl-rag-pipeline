"""Tests for top-level ETL orchestration."""

from unittest.mock import patch

from src.pipeline.etl import run_etl


def test_run_etl_calls_stages_in_order() -> None:
    """The top-level runner executes extract, transform, then load."""
    stage_calls = []

    with (
        patch(
            "src.pipeline.etl.extract",
            side_effect=lambda: stage_calls.append("extract"),
        ),
        patch(
            "src.pipeline.etl.transform",
            side_effect=lambda: stage_calls.append("transform"),
        ),
        patch("src.pipeline.etl.load", side_effect=lambda: stage_calls.append("load")),
    ):
        run_etl()

    assert stage_calls == ["extract", "transform", "load"]
