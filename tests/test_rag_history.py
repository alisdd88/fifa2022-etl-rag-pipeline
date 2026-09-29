"""Tests for persisted RAG query history."""

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.rag.history import save_query_history


class SaveQueryHistoryTests(unittest.TestCase):
    """Verify successful answers are appended in the UI history format."""

    def test_save_query_history_appends_record(self) -> None:
        """A new answer is appended without replacing earlier history."""
        sources = [
            {
                "id": "chunk_1",
                "content": "Montiel scored the winning penalty.",
                "metadata": {
                    "article_id": "article_1",
                    "match_id": "2022_final_argentina_france",
                    "src": "article_1.txt",
                },
                "distance": 0.1,
            }
        ]

        existing_record = {
            "query": "Earlier question",
            "answer": "Earlier answer",
            "sources": [],
            "created_at": "2026-01-01T00:00:00+00:00",
        }

        with TemporaryDirectory() as temporary_directory:
            history_path = Path(temporary_directory) / "query_history.json"
            history_path.write_text(
                json.dumps([existing_record]),
                encoding="utf-8",
            )

            record = save_query_history(
                " Who scored in the final? ",
                " Montiel scored [Source 1]. ",
                sources,
                history_path=history_path,
            )
            saved_history = json.loads(history_path.read_text(encoding="utf-8"))

        self.assertEqual(saved_history, [existing_record, record])
        self.assertEqual(record["query"], "Who scored in the final?")
        self.assertEqual(record["answer"], "Montiel scored [Source 1].")
        self.assertEqual(record["sources"], sources)
        created_at = datetime.fromisoformat(record["created_at"])
        self.assertIsNotNone(created_at.tzinfo)

    def test_save_query_history_rejects_non_list_file(self) -> None:
        """Malformed history is not silently replaced with a new list."""
        with TemporaryDirectory() as temporary_directory:
            history_path = Path(temporary_directory) / "query_history.json"
            history_path.write_text('{"query": "wrong shape"}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must contain a JSON list"):
                save_query_history(
                    "Who won?",
                    "Argentina won.",
                    [],
                    history_path=history_path,
                )

            unchanged_content = history_path.read_text(encoding="utf-8")

        self.assertEqual(unchanged_content, '{"query": "wrong shape"}')


if __name__ == "__main__":
    unittest.main()
