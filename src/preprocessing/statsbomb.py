"""StatsBomb preprocessing entry points."""

import pandas as pd

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.preprocessing.preprocessing_helpers import process_events
from src.utils.io import load_raw_data


def normalize_statsbomb() -> None:
    """Normalize raw StatsBomb records into the project data model."""
    raw_matches, raw_lineups, raw_events = import_dataframes()
    transform_matches(raw_matches)
    transform_lineups(raw_lineups)
    transform_events(raw_events)


def transform_matches(raw_matches: pd.DataFrame) -> None:
    """Transform raw match records into match and competition tables."""
    statsbomb_processed_dir = PROCESSED_DATA_DIR / "statsbomb"
    statsbomb_processed_dir.mkdir(parents=True, exist_ok=True)

    columns = [
        "match_id",
        "match_date",
        "kick_off",
        "home_score",
        "away_score",
        "match_status",
        "match_week",
        "competition_id",
        "competition_country_name",
        "competition_name",
        "competition",
        "competition_stage_id",
        "competition_stage",
        "season_id",
        "season",
        "home_team_id",
        "home_team",
        "home_team_country_id",
        "home_team_country_name",
        "away_team_id",
        "away_team",
        "away_team_country_id",
        "away_team_country_name",
        "stadium_id",
        "stadium",
        "stadium_country_id",
        "stadium_country_name",
        "referee_id",
        "referee",
        "referee_country_id",
        "referee_country_name",
        "home_managers",
        "away_managers",
        "home_manager_id",
        "home_manager_name",
        "home_manager_dob",
        "home_manager_country_id",
        "home_manager_country_name",
        "away_manager_id",
        "away_manager_name",
        "away_manager_dob",
        "away_manager_country_id",
        "away_manager_country_name",
        "data_version",
        "shot_fidelity_version",
        "xy_fidelity_version",
    ]

    # Step 1: Select the required columns without modifying the raw DataFrame.
    missing_columns = set(columns).difference(raw_matches.columns)
    if missing_columns:
        raise ValueError(f"Raw matches are missing columns: {sorted(missing_columns)}")

    matches = raw_matches[columns].copy()

    # Step 2: Preserve the provider ID and create the project canonical ID.
    matches = matches.rename(columns={"match_id": "statsbomb_match_id"})
    canonical_columns = ["season", "competition_stage", "home_team", "away_team"]

    if matches[canonical_columns].isnull().any().any():
        raise ValueError("Canonical match ID fields must not contain null values.")

    canonical_parts = (
        matches[canonical_columns]
        .astype(str)
        .apply(
            lambda column: (
                column.str.strip()
                .str.lower()
                .str.replace(r"[^a-z0-9]+", "_", regex=True)
                .str.strip("_")
            )
        )
    )
    matches.insert(0, "canonical_id", canonical_parts.agg("_".join, axis=1))

    if not matches["canonical_id"].is_unique:
        raise ValueError("Canonical match IDs must be unique.")

    # Step 3: Create one competition-season record while retaining its IDs on matches.
    competition_columns = [
        "competition_id",
        "competition_name",
        "competition_country_name",
        "competition",
        "season_id",
        "season",
    ]
    competition = matches[competition_columns].drop_duplicates().reset_index(drop=True)
    matches = matches.drop(
        columns=[
            "competition_name",
            "competition_country_name",
            "competition",
            "season",
        ]
    )

    # Step 4: Save reproducible processed tables.
    competition.to_csv(statsbomb_processed_dir / "competition.csv", index=False)
    matches.to_csv(statsbomb_processed_dir / "match.csv", index=False)


def transform_events(raw_events: pd.DataFrame) -> None:
    """Transform raw StatsBomb events into normalized key-event actions."""
    statsbomb_processed_dir = PROCESSED_DATA_DIR / "statsbomb"
    statsbomb_processed_dir.mkdir(parents=True, exist_ok=True)

    events_columns = [
        "match_id",
        "id",
        "index",
        "period",
        "minute",
        "second",
        "timestamp",
        "duration",
        "type",
        "player_id",
        "team_id",
        "team",
        "player",
        "foul_committed_penalty",
        "foul_committed_offensive",
        "foul_committed_type",
        "foul_committed_advantage",
        "bad_behaviour_card",
        "foul_committed_card",
        "shot_outcome",
        "shot_saved_to_post",
        "shot_type",
        "substitution_replacement",
        "substitution_replacement_id",
        "substitution_outcome",
        "substitution_outcome_id",
    ]

    # Step 1: Validate and select columns without modifying the raw DataFrame.
    missing_columns = set(events_columns).difference(raw_events.columns)
    if missing_columns:
        raise ValueError(f"Raw events are missing columns: {sorted(missing_columns)}")

    events = raw_events[events_columns].copy()
    events = events.rename(
        columns={
            "match_id": "statsbomb_match_id",
            "id": "statsbomb_event_id",
            "index": "statsbomb_event_index",
        }
    )

    # Step 2: Retain source events that can produce approved key-event actions.
    source_event_types = [
        "Foul Committed",
        "Shot",
        "Bad Behaviour",
        "Substitution",
    ]
    events = events[events["type"].isin(source_event_types)].copy()

    # Step 3: Link every event to the project's canonical match identifier.
    matches = pd.read_csv(statsbomb_processed_dir / "match.csv")
    match_columns = {"statsbomb_match_id", "canonical_id"}
    missing_match_columns = match_columns.difference(matches.columns)
    if missing_match_columns:
        raise ValueError(
            f"Processed matches are missing columns: {sorted(missing_match_columns)}"
        )

    match_links = matches[["statsbomb_match_id", "canonical_id"]].rename(
        columns={"canonical_id": "match_id"}
    )
    events = events.merge(
        match_links,
        on="statsbomb_match_id",
        how="left",
        validate="many_to_one",
    )
    if events["match_id"].isnull().any():
        raise ValueError("Every processed event must link to a project match ID.")

    # Step 4: Create a readable project event identifier.
    events["event_id"] = (
        events["match_id"].astype(str)
        + "_"
        + events["statsbomb_event_index"].astype(str)
    )
    if not events["event_id"].is_unique:
        raise ValueError("Project event IDs must be unique before event processing.")

    # Step 5: Build goals, cards, and paired substitution actions with metadata.
    processed_events = process_events(events)

    allowed_event_types = {"card", "goal", "substitution"}
    unexpected_event_types = set(processed_events["event_type"]) - allowed_event_types
    if unexpected_event_types:
        raise ValueError(f"Unexpected event types: {sorted(unexpected_event_types)}")

    mandatory_columns = ["event_id", "match_id", "player_id", "team_id", "event_type"]
    null_counts = processed_events[mandatory_columns].isnull().sum()
    if null_counts.any():
        raise ValueError(
            f"Mandatory event fields contain nulls: {null_counts[null_counts > 0].to_dict()}"
        )

    if not processed_events["event_id"].is_unique:
        raise ValueError("Processed event IDs must be unique.")
    if (processed_events["period"] <= 0).any():
        raise ValueError("Event periods must be greater than zero.")
    if (processed_events["minute"] < 0).any():
        raise ValueError("Event minutes must not be negative.")
    if (processed_events["second"] < 0).any():
        raise ValueError("Event seconds must not be negative.")
    if processed_events["timestamp"].isnull().any():
        raise ValueError("Event timestamps must not contain null values.")
    if (
        (processed_events["event_type"] == "goal") & (processed_events["period"] == 5)
    ).any():
        raise ValueError("Shootout conversions must not be classified as match goals.")

    # Step 6: Save the final event table for inspection and later loading.
    processed_events.to_csv(
        statsbomb_processed_dir / "events.csv",
        index=False,
    )


def transform_lineups(raw_lineups):
    pass


def import_dataframes():
    statsbomb_raw_dir = RAW_DATA_DIR / "statsbomb"

    raw_matches = load_raw_data(statsbomb_raw_dir / "raw_matches.json")
    raw_lineups = load_raw_data(statsbomb_raw_dir / "raw_lineups.json")
    raw_events = load_raw_data(statsbomb_raw_dir / "raw_events.json")

    return raw_matches, raw_lineups, raw_events
