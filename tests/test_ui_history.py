"""Tests for safely reading existing query history for the UI."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.ui.history import format_history_datetime, load_query_history


class LoadQueryHistoryTests(unittest.TestCase):
    """Verify only existing, displayable history records reach the UI."""

    def test_loads_valid_records_and_ignores_invalid_records(self) -> None:
        """Required fields follow the structure written by the RAG pipeline."""
        valid_record = {
            "query": " Who won? ",
            "answer": " Argentina won. ",
            "sources": [{"id": "chunk_1", "content": "Argentina won."}],
            "created_at": "2022-12-18T18:00:00+00:00",
        }
        invalid_records = [
            {"query": "Missing answer", "sources": []},
            {"query": "", "answer": "Answer", "sources": []},
            {"query": "Question", "answer": "Answer", "sources": "wrong"},
            "wrong record type",
        ]

        with TemporaryDirectory() as temporary_directory:
            history_path = Path(temporary_directory) / "query_history.json"
            history_path.write_text(
                json.dumps([valid_record, *invalid_records]), encoding="utf-8"
            )
            result = load_query_history(history_path)

        self.assertEqual(
            result,
            [
                {
                    "query": "Who won?",
                    "answer": "Argentina won.",
                    "sources": valid_record["sources"],
                    "created_at": "2022-12-18T18:00:00+00:00",
                }
            ],
        )

    def test_returns_empty_list_for_empty_or_malformed_history(self) -> None:
        """An unusable history file hides History instead of raising an error."""
        malformed_values = ["[]", "not JSON", '{"query": "wrong shape"}']

        with TemporaryDirectory() as temporary_directory:
            history_path = Path(temporary_directory) / "query_history.json"
            for value in malformed_values:
                with self.subTest(value=value):
                    history_path.write_text(value, encoding="utf-8")
                    self.assertEqual(load_query_history(history_path), [])

    def test_returns_empty_list_when_history_file_is_missing(self) -> None:
        """A missing history file is handled like an empty history."""
        with TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.json"
            self.assertEqual(load_query_history(missing_path), [])

    def test_formats_valid_iso_datetime_and_ignores_invalid_value(self) -> None:
        """History dates are readable without making timestamps mandatory."""
        self.assertEqual(
            format_history_datetime("2022-12-18T18:00:00+00:00"),
            "Dec 18, 2022 at 18:00 UTC",
        )
        self.assertIsNone(format_history_datetime("not a timestamp"))


if __name__ == "__main__":
    unittest.main()
