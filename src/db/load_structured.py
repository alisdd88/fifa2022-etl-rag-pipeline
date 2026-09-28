"""Load processed StatsBomb CSV files into PostgreSQL."""

import csv
import io
import json
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql

from config.settings import PROCESSED_DATA_DIR
from src.db.db import connect_database
from src.db.schema import create_schema

STATSBOMB_PROCESSED_DIR = PROCESSED_DATA_DIR / "statsbomb"

TABLE_LOADS = (
    (
        "competition",
        "competition.csv",
        [
            "competition_id",
            "competition_name",
            "competition_country_name",
            "competition",
            "season_id",
            "season",
        ],
        ["competition_id", "season_id"],
    ),
    (
        "matches",
        "match.csv",
        [
            "match_id",
            "statsbomb_match_id",
            "match_date",
            "kick_off",
            "home_score",
            "away_score",
            "match_status",
            "match_week",
            "competition_id",
            "competition_stage_id",
            "competition_stage",
            "season_id",
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
        ],
        ["match_id"],
    ),
    (
        "lineups",
        "lineups.csv",
        [
            "match_id",
            "statsbomb_match_id",
            "player_id",
            "player_name",
            "player_nickname",
            "player_display_name",
            "jersey_number",
            "country",
            "team",
        ],
        ["match_id", "player_id"],
    ),
    (
        "events",
        "events.csv",
        [
            "statsbomb_match_id",
            "statsbomb_event_id",
            "statsbomb_event_index",
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
            "match_id",
            "event_id",
            "event_type",
            "metadata",
        ],
        ["event_id"],
    ),
)

SOURCE_COLUMN_OVERRIDES = {
    "matches": {"match_id": "canonical_id"},
    "lineups": {"match_id": "canonical_id"},
}


def _source_columns(table_name: str, database_columns: list[str]) -> list[str]:
    """Return CSV column names corresponding to the database columns."""
    overrides = SOURCE_COLUMN_OVERRIDES.get(table_name, {})
    return [overrides.get(column, column) for column in database_columns]


def _read_csv_text(
    path: Path,
    expected_columns: list[str],
    normalize_event_player_id: bool = False,
) -> str:
    """Read and validate CSV text, normalizing event player IDs when needed."""
    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"Unexpected columns in {path.name}: expected {expected_columns}, "
                f"got {reader.fieldnames}"
            )

        if not normalize_event_player_id:
            input_file.seek(0)
            return input_file.read()

        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=expected_columns)
        writer.writeheader()
        for row in reader:
            row["player_id"] = str(int(Decimal(row["player_id"])))
            writer.writerow(row)
        return output.getvalue()


def _copy_csv(
    connection: psycopg.Connection,
    table_name: str,
    file_name: str,
    database_columns: list[str],
) -> None:
    """Copy one validated processed CSV into its database table."""
    source_columns = _source_columns(table_name, database_columns)
    csv_text = _read_csv_text(
        STATSBOMB_PROCESSED_DIR / file_name,
        source_columns,
        normalize_event_player_id=table_name == "events",
    )
    copy_statement = sql.SQL(
        "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ).format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, database_columns)),
    )
    with connection.cursor().copy(copy_statement) as copy:
        copy.write(csv_text)


def _normalize_value(table_name: str, column: str, value: object) -> str:
    """Convert CSV and PostgreSQL values to a comparable text form."""
    if value is None:
        return ""
    if column == "metadata":
        parsed_value = json.loads(value) if isinstance(value, str) else value
        return json.dumps(parsed_value, sort_keys=True, separators=(",", ":"))
    if table_name == "events" and column == "player_id":
        return str(int(Decimal(str(value))))
    if isinstance(value, time):
        return value.isoformat(timespec="milliseconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _csv_rows(
    table_name: str,
    file_name: str,
    database_columns: list[str],
) -> set[tuple[str, ...]]:
    """Read normalized full rows from one processed CSV."""
    source_columns = _source_columns(table_name, database_columns)
    with (STATSBOMB_PROCESSED_DIR / file_name).open(
        encoding="utf-8", newline=""
    ) as input_file:
        return {
            tuple(
                _normalize_value(table_name, database_column, row[source_column])
                for database_column, source_column in zip(
                    database_columns, source_columns, strict=True
                )
            )
            for row in csv.DictReader(input_file)
        }


def validate_structured_load(
    connection: psycopg.Connection,
) -> dict[str, int]:
    """Compare every CSV row and column with the loaded database records."""
    validated_counts = {}
    for table_name, file_name, database_columns, _ in TABLE_LOADS:
        expected_rows = _csv_rows(table_name, file_name, database_columns)
        selected_columns = sql.SQL(", ").join(map(sql.Identifier, database_columns))
        database_rows = connection.execute(
            sql.SQL("SELECT {} FROM {}").format(
                selected_columns,
                sql.Identifier(table_name),
            )
        ).fetchall()
        actual_rows = {
            tuple(
                _normalize_value(table_name, column, value)
                for column, value in zip(database_columns, row, strict=True)
            )
            for row in database_rows
        }

        if len(database_rows) != len(expected_rows):
            raise ValueError(
                f"Row-count mismatch for {table_name}: CSV has "
                f"{len(expected_rows)}, database has {len(database_rows)}"
            )
        if actual_rows != expected_rows:
            raise ValueError(f"Row-content mismatch for {table_name}.")
        validated_counts[table_name] = len(database_rows)

    return validated_counts


def load_structured_data() -> dict[str, int]:
    """Replace database rows with the processed CSV snapshot and validate it."""
    with connect_database() as connection:
        create_schema(connection)
        connection.execute("TRUNCATE TABLE events, lineups, matches, competition")
        for table_name, file_name, database_columns, _ in TABLE_LOADS:
            _copy_csv(connection, table_name, file_name, database_columns)
        return validate_structured_load(connection)
