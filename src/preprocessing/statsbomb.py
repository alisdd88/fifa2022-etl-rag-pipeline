"""StatsBomb preprocessing entry points."""

import pandas as pd

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
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


def transform_lineups(raw_lineups):
    pass


def transform_events(raw_events):
    pass


def import_dataframes():
    statsbomb_raw_dir = RAW_DATA_DIR / "statsbomb"

    raw_matches = load_raw_data(statsbomb_raw_dir / "raw_matches.json")
    raw_lineups = load_raw_data(statsbomb_raw_dir / "raw_lineups.json")
    raw_events = load_raw_data(statsbomb_raw_dir / "raw_events.json")

    return raw_matches, raw_lineups, raw_events
