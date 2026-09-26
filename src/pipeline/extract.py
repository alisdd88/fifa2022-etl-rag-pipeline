"""Orchestration for the extraction stage."""

from config.settings import RAW_DATA_DIR
from src.extraction.statsbomb import fetch_statsbomb_data
from src.utils.io import save_raw_dataframe


def extract() -> None:
    """Fetch source data and save immutable raw artifacts."""
    # Step 1: Fetch structured StatsBomb data.
    matches, events, lineups = fetch_statsbomb_data()

    # Step 2: Save each DataFrame as an immutable raw JSON artifact.
    statsbomb_raw_dir = RAW_DATA_DIR / "statsbomb"
    save_raw_dataframe(matches, statsbomb_raw_dir / "raw_matches.json")
    save_raw_dataframe(events, statsbomb_raw_dir / "raw_events.json")
    save_raw_dataframe(lineups, statsbomb_raw_dir / "raw_lineups.json")
