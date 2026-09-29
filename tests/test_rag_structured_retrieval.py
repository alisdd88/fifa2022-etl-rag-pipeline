"""Tests for validating generated structured-retrieval SQL."""

import unittest
from unittest.mock import MagicMock, call, patch

from psycopg.rows import dict_row

from config.settings import DATABASE_SCHEMA
from src.rag.retrieval import structured_retriever
from src.rag.retrieval.structured_retriever import (
    execute_sql,
    generate_sql,
    validate_sql,
)


class StructuredSqlValidationTests(unittest.TestCase):
    """Verify that only single, read-only queries over approved tables pass."""

    def test_generate_sql_receives_exact_schema_and_retrieval_guidance(self) -> None:
        """SQL generation receives the question, DDL, and event semantics."""
        generated_sql = "SELECT e.player FROM events AS e"

        with patch.object(
            structured_retriever.ollama,
            "generate",
            return_value={"response": generated_sql},
        ) as generate:
            result = generate_sql("Who scored?")

        self.assertEqual(result, generated_sql)
        request = generate.call_args.kwargs
        self.assertIn(DATABASE_SCHEMA, request["system"])
        self.assertIn("Use `event_type` to select", request["system"])
        self.assertIn("Do not infer goalscorers from `lineups`", request["system"])
        self.assertIn("Who scored?", request["prompt"])

    def test_accepts_selects_over_approved_tables(self) -> None:
        """Simple selects, joins, and read-only CTEs may use approved tables."""
        valid_queries = (
            "SELECT home_team, away_team FROM matches",
            """
            SELECT e.player, m.match_date
            FROM events AS e
            JOIN matches AS m ON m.match_id = e.match_id
            """,
            """
            WITH final_matches AS (
                SELECT match_id FROM public.matches
            )
            SELECT e.player
            FROM events AS e
            JOIN final_matches AS f ON f.match_id = e.match_id
            """,
        )

        for sql_query in valid_queries:
            with self.subTest(sql_query=sql_query):
                self.assertTrue(validate_sql(sql_query))

    def test_rejects_empty_or_invalid_sql(self) -> None:
        """Blank input and text that PostgreSQL cannot parse are rejected."""
        for sql_query in ("", "   ", "SELECT FROM"):
            with self.subTest(sql_query=sql_query):
                self.assertFalse(validate_sql(sql_query))

    def test_rejects_non_select_and_destructive_statements(self) -> None:
        """Data-changing and administrative statements cannot pass validation."""
        rejected_queries = (
            "INSERT INTO matches (match_id) VALUES ('match-1')",
            "UPDATE matches SET home_score = 3",
            "DELETE FROM events",
            "DROP TABLE events",
            "ALTER TABLE matches ADD COLUMN notes TEXT",
            "TRUNCATE TABLE lineups",
            "CREATE TABLE backup AS SELECT * FROM matches",
            "GRANT SELECT ON matches TO analyst",
            "REVOKE SELECT ON matches FROM analyst",
            "SELECT * INTO events FROM matches",
            "WITH removed AS (DELETE FROM events RETURNING *) SELECT * FROM removed",
        )

        for sql_query in rejected_queries:
            with self.subTest(sql_query=sql_query):
                self.assertFalse(validate_sql(sql_query))

    def test_rejects_multiple_statements(self) -> None:
        """A valid first query cannot hide an additional statement."""
        self.assertFalse(validate_sql("SELECT * FROM matches; DROP TABLE events"))
        self.assertFalse(validate_sql("SELECT * FROM matches;;"))

    def test_rejects_comments(self) -> None:
        """Generated SQL cannot contain line or block comments."""
        commented_queries = (
            "SELECT * FROM matches -- ignore the rest",
            "SELECT /* generated */ * FROM matches",
        )

        for sql_query in commented_queries:
            with self.subTest(sql_query=sql_query):
                self.assertFalse(validate_sql(sql_query))

    def test_execute_sql_rejects_invalid_query_before_connecting(self) -> None:
        """Unsafe SQL never reaches PostgreSQL."""
        with (
            patch.object(structured_retriever, "connect_database") as connect,
            self.assertRaisesRegex(ValueError, "failed read-only validation"),
        ):
            execute_sql("DELETE FROM events")

        connect.assert_not_called()

    def test_execute_sql_returns_dictionary_rows_from_read_only_transaction(
        self,
    ) -> None:
        """Validated SQL is executed with read-only and timeout safeguards."""
        sql_query = "SELECT home_team, away_team FROM matches"
        expected_rows = [
            {"home_team": "Argentina", "away_team": "France"},
        ]
        connection_manager = MagicMock()
        connection = connection_manager.__enter__.return_value
        cursor_manager = MagicMock()
        cursor = cursor_manager.__enter__.return_value
        connection.cursor.return_value = cursor_manager
        cursor.fetchall.return_value = expected_rows

        with (
            patch.object(
                structured_retriever,
                "connect_database",
                return_value=connection_manager,
            ) as connect,
            self.assertLogs(structured_retriever.__name__, level="INFO") as logs,
        ):
            result = execute_sql(sql_query)

        connect.assert_called_once_with()
        self.assertEqual(
            connection.execute.call_args_list,
            [
                call("SET TRANSACTION READ ONLY"),
                call("SET LOCAL statement_timeout = '5s'"),
            ],
        )
        connection.cursor.assert_called_once_with(row_factory=dict_row)
        cursor.execute.assert_called_once_with(sql_query)
        cursor.fetchall.assert_called_once_with()
        self.assertEqual(result, expected_rows)
        self.assertIn("Structured SQL returned 1 row(s).", "\n".join(logs.output))

    def test_execute_sql_warns_when_query_returns_no_rows(self) -> None:
        """An empty database result is visible in diagnostic logs."""
        connection_manager = MagicMock()
        connection = connection_manager.__enter__.return_value
        cursor_manager = MagicMock()
        cursor = cursor_manager.__enter__.return_value
        connection.cursor.return_value = cursor_manager
        cursor.fetchall.return_value = []

        with (
            patch.object(
                structured_retriever,
                "connect_database",
                return_value=connection_manager,
            ),
            self.assertLogs(structured_retriever.__name__, level="WARNING") as logs,
        ):
            result = execute_sql("SELECT match_id FROM matches")

        self.assertEqual(result, [])
        self.assertIn("Structured SQL returned 0 rows", "\n".join(logs.output))

    def test_rejects_unapproved_tables_and_schemas(self) -> None:
        """Queries may access only approved project tables in the public schema."""
        rejected_queries = (
            "SELECT * FROM metadata",
            "SELECT * FROM users",
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM pg_catalog.pg_tables",
            "SELECT * FROM private.matches",
            "SELECT * FROM fifa.public.matches",
        )

        for sql_query in rejected_queries:
            with self.subTest(sql_query=sql_query):
                self.assertFalse(validate_sql(sql_query))


if __name__ == "__main__":
    unittest.main()
