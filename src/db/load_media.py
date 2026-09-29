"""Load processed article and media metadata into PostgreSQL."""

import json
from pathlib import Path

import psycopg

from config.settings import PROCESSED_DATA_DIR, PROJECT_ROOT
from src.db.db import connect_database
from src.db.schema import create_schema

ARTICLE_METADATA_DIR = PROCESSED_DATA_DIR / "articles" / "metadata"
ARTICLE_REQUIRED_KEYS = ("article_id", "match_id", "source", "text_path")
ARTICLE_INSERT_STATEMENT = """
INSERT INTO metadata (
    metadata_id,
    match_id,
    source,
    type,
    file_path,
    metadata_path
)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def _project_relative_path(path: Path) -> str:
    """Return a portable project-relative path."""
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _read_article_rows() -> list[tuple[str, ...]]:
    """Read processed article JSON files and map them to metadata rows."""
    metadata_files = sorted(ARTICLE_METADATA_DIR.glob("*.json"))
    if not metadata_files:
        raise FileNotFoundError(
            f"No processed article metadata files found in {ARTICLE_METADATA_DIR}"
        )

    rows = []
    metadata_ids = set()
    for metadata_path in metadata_files:
        with metadata_path.open(encoding="utf-8") as input_file:
            article = json.load(input_file)
        if not isinstance(article, dict):
            raise TypeError(f"Article metadata must be an object: {metadata_path.name}")

        missing_keys = [key for key in ARTICLE_REQUIRED_KEYS if key not in article]
        if missing_keys:
            raise ValueError(f"Missing keys in {metadata_path.name}: {missing_keys}")

        values = {key: article[key] for key in ARTICLE_REQUIRED_KEYS}
        invalid_keys = [
            key
            for key, value in values.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if invalid_keys:
            raise ValueError(
                f"Expected non-empty strings in {metadata_path.name}: {invalid_keys}"
            )

        metadata_id = values["article_id"]
        if metadata_id in metadata_ids:
            raise ValueError(f"Duplicate article ID: {metadata_id}")

        file_path = values["text_path"]
        if not (PROJECT_ROOT / file_path).is_file():
            raise FileNotFoundError(
                f"Article text file does not exist for {metadata_id}: {file_path}"
            )

        rows.append(
            (
                metadata_id,
                values["match_id"],
                values["source"],
                "article",
                file_path,
                _project_relative_path(metadata_path),
            )
        )
        metadata_ids.add(metadata_id)

    return rows


def validate_article_load(
    connection: psycopg.Connection,
    expected_rows: list[tuple[str, ...]],
) -> int:
    """Compare every loaded article metadata value with its processed source."""
    database_rows = connection.execute(
        """
        SELECT metadata_id, match_id, source, type, file_path, metadata_path
        FROM metadata
        WHERE type = %s
        """,
        ("article",),
    ).fetchall()

    if len(database_rows) != len(expected_rows):
        raise ValueError(
            "Article metadata row-count mismatch: "
            f"expected {len(expected_rows)}, database has {len(database_rows)}"
        )
    if set(database_rows) != set(expected_rows):
        raise ValueError("Article metadata row-content mismatch.")
    return len(database_rows)


def insert_article() -> int:
    """Replace article metadata rows from all processed article JSON files."""
    article_rows = _read_article_rows()
    with connect_database() as connection:
        create_schema(connection)
        connection.execute("DELETE FROM metadata WHERE type = %s", ("article",))
        with connection.cursor() as cursor:
            cursor.executemany(ARTICLE_INSERT_STATEMENT, article_rows)
        return validate_article_load(connection, article_rows)


def insert_image_metadata() -> None:
    """Insert metadata for one processed image."""


def insert_audio_metadata() -> None:
    """Insert metadata for one processed audio item."""
