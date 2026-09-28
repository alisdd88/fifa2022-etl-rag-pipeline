"""Tests for extraction-stage orchestration."""

from unittest.mock import call, patch

from src.pipeline.extract import extract


def test_extract_saves_statsbomb_data_then_extracts_articles() -> None:
    """The extraction stage runs both approved structured and article sources."""
    matches = object()
    events = object()
    lineups = object()

    with (
        patch(
            "src.pipeline.extract.fetch_statsbomb_data",
            return_value=(matches, events, lineups),
        ),
        patch("src.pipeline.extract.save_raw_dataframe") as save_raw_dataframe,
        patch("src.pipeline.extract.extract_articles") as extract_articles,
    ):
        extract()

    statsbomb_directory = save_raw_dataframe.call_args_list[0].args[1].parent
    assert save_raw_dataframe.call_args_list == [
        call(matches, statsbomb_directory / "raw_matches.json"),
        call(events, statsbomb_directory / "raw_events.json"),
        call(lineups, statsbomb_directory / "raw_lineups.json"),
    ]
    extract_articles.assert_called_once_with()
