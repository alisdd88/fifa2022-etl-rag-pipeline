"""Tests for the command-line RAG entry point."""

import unittest
from unittest.mock import patch

import app


class AppTests(unittest.TestCase):
    """Verify a user query is passed to the complete RAG pipeline."""

    def test_main_reads_query_and_prints_answer(self) -> None:
        """The command-line entry point requires only one user question."""
        with (
            patch.object(app, "configure_logging") as configure_logging,
            patch("builtins.input", return_value="Who won the final?") as read_input,
            patch.object(
                app,
                "answer_query",
                return_value={
                    "answer": "Argentina won [Source 1].",
                    "retrieved_chunks": [],
                },
            ) as answer_query,
            patch("builtins.print") as print_output,
        ):
            app.main()

        configure_logging.assert_called_once_with()
        read_input.assert_called_once_with("Ask a FIFA World Cup 2022 question: ")
        answer_query.assert_called_once_with("Who won the final?")
        print_output.assert_called_once_with("Argentina won [Source 1].")


if __name__ == "__main__":
    unittest.main()
