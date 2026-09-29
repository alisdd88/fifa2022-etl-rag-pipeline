"""Tests for PostgreSQL schema creation."""

from unittest.mock import MagicMock

from src.db.schema import SCHEMA_STATEMENTS, create_schema


def test_schema_contains_metadata_table_after_matches() -> None:
    """The shared metadata table is created after its referenced match table."""
    match_index = next(
        index
        for index, statement in enumerate(SCHEMA_STATEMENTS)
        if "CREATE TABLE IF NOT EXISTS matches" in statement
    )
    metadata_index = next(
        index
        for index, statement in enumerate(SCHEMA_STATEMENTS)
        if "CREATE TABLE IF NOT EXISTS metadata" in statement
    )
    metadata_statement = SCHEMA_STATEMENTS[metadata_index]

    assert metadata_index > match_index
    assert "metadata_id TEXT PRIMARY KEY" in metadata_statement
    assert "match_id TEXT NOT NULL" in metadata_statement
    assert "source TEXT NOT NULL" in metadata_statement
    assert "type TEXT NOT NULL" in metadata_statement
    assert "file_path TEXT NOT NULL" in metadata_statement
    assert "metadata_path TEXT NOT NULL" in metadata_statement
    assert "FOREIGN KEY (match_id) REFERENCES matches (match_id)" in (
        metadata_statement
    )


def test_create_schema_executes_metadata_table_statement() -> None:
    """Normal schema creation includes the metadata table automatically."""
    connection = MagicMock()

    create_schema(connection)

    executed_statements = [call.args[0] for call in connection.execute.call_args_list]
    assert executed_statements == list(SCHEMA_STATEMENTS)
    assert any(
        "CREATE TABLE IF NOT EXISTS metadata" in statement
        for statement in executed_statements
    )
