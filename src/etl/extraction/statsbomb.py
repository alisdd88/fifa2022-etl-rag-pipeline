"""Fetch structured FIFA World Cup 2022 data from StatsBomb."""

import logging

import pandas as pd
from statsbombpy import sb

logger = logging.getLogger(__name__)

# StatsBomb identifiers for the FIFA World Cup 2022.
COMPETITION_ID = 43
SEASON_ID = 106

DEFAULT_STAGES = ("Semi-finals", "Final")


def fetch_statsbomb_data(
    competition_id: int = COMPETITION_ID,
    season_id: int = SEASON_ID,
    selected_stages: tuple[str, ...] = DEFAULT_STAGES,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch selected matches and their events and lineups.

    Returns:
        A tuple containing target matches, events, and lineups.
    """
    all_matches = sb.matches(
        competition_id=competition_id,
        season_id=season_id,
    )

    required_columns = {"match_id", "competition_stage"}
    missing_columns = required_columns.difference(all_matches.columns)

    if missing_columns:
        raise ValueError(
            f"StatsBomb matches are missing columns: {sorted(missing_columns)}"
        )

    available_stages = set(all_matches["competition_stage"].dropna().unique())
    missing_stages = set(selected_stages).difference(available_stages)

    if missing_stages:
        raise ValueError(
            f"Stages not found in StatsBomb data: {sorted(missing_stages)}"
        )

    target_matches = (
        all_matches[all_matches["competition_stage"].isin(selected_stages)]
        .copy()
        .reset_index(drop=True)
    )

    event_frames = []
    lineup_frames = []

    for match_id in target_matches["match_id"]:
        try:
            events = sb.events(match_id=match_id).copy()
            events["match_id"] = match_id
            event_frames.append(events)

            lineups = sb.lineups(match_id=match_id)

            for team_name, lineup in lineups.items():
                lineup = lineup.copy()
                lineup["match_id"] = match_id
                lineup["team"] = team_name
                lineup_frames.append(lineup)

        except Exception as error:
            raise RuntimeError(
                f"Failed to fetch StatsBomb data for match_id={match_id}"
            ) from error

    if not event_frames:
        raise ValueError("No event data was returned for the selected matches.")

    if not lineup_frames:
        raise ValueError("No lineup data was returned for the selected matches.")

    events_df = pd.concat(event_frames, ignore_index=True)
    lineups_df = pd.concat(lineup_frames, ignore_index=True)

    logger.info(
        "Fetched %d matches, %d events, and %d lineup entries.",
        len(target_matches),
        len(events_df),
        len(lineups_df),
    )

    return target_matches, events_df, lineups_df
