"""Tests for the Streamlit RAG interface coordination."""

import unittest
from unittest.mock import MagicMock, Mock, call, patch

import app


class AppTests(unittest.TestCase):
    """Verify navigation and the shared answer preview behavior."""

    def test_main_hides_history_navigation_when_no_valid_records(self) -> None:
        """Empty history opens Ask directly without exposing History."""
        fake_streamlit = Mock()
        fake_streamlit.session_state = {}

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "configure_logging"),
            patch.object(app, "load_query_history", return_value=[]),
            patch.object(app, "render_ask_page") as render_ask,
            patch.object(app, "render_history_page") as render_history,
        ):
            app.main()

        fake_streamlit.sidebar.radio.assert_not_called()
        render_ask.assert_called_once_with()
        render_history.assert_not_called()

    def test_main_exposes_history_navigation_when_records_exist(self) -> None:
        """At least one valid record makes the History destination available."""
        history = [
            {
                "query": "Who won?",
                "answer": "Argentina won.",
                "sources": [],
                "created_at": "2022-12-18T18:00:00+00:00",
            }
        ]
        fake_streamlit = Mock()
        fake_streamlit.session_state = {}
        fake_streamlit.sidebar.radio.return_value = "History"

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "configure_logging"),
            patch.object(app, "load_query_history", return_value=history),
            patch.object(app, "render_ask_page") as render_ask,
            patch.object(app, "render_history_page") as render_history,
        ):
            app.main()

        fake_streamlit.sidebar.radio.assert_called_once_with(
            "Navigation", ("Ask", "History"), key="page"
        )
        render_history.assert_called_once_with(history)
        render_ask.assert_not_called()

    def test_new_answer_uses_shared_preview(self) -> None:
        """A newly generated response is mapped to the shared result page."""
        fake_streamlit = MagicMock()
        fake_streamlit.session_state = {}
        fake_streamlit.text_input.return_value = "Who won?"
        fake_streamlit.radio.return_value = "structured"
        fake_streamlit.form_submit_button.return_value = True
        result = {
            "answer": "Argentina won [Source 1].",
            "retrieved_chunks": [{"id": "chunk_1"}],
        }

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "answer_query", return_value=result) as answer_query,
            patch.object(app, "render_answer_preview") as render_preview,
        ):
            app.render_ask_page()

        fake_streamlit.radio.assert_called_once_with(
            "Retrieval method",
            ("semantic", "structured"),
            format_func=str.title,
            horizontal=True,
            key="retrieval_router",
        )
        answer_query.assert_called_once_with("Who won?", router="structured")
        render_preview.assert_called_once_with(
            {
                "question": "Who won?",
                "answer": "Argentina won [Source 1].",
                "sources": [{"id": "chunk_1"}],
            }
        )

    def test_selected_history_item_uses_shared_preview(self) -> None:
        """Selecting history reaches the same result renderer as a new answer."""
        history = [
            {
                "query": "Who won?",
                "answer": "Argentina won.",
                "sources": [],
            }
        ]
        fake_streamlit = Mock()
        fake_streamlit.session_state = {"selected_history_index": 0}
        fake_streamlit.button.return_value = False

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "render_answer_preview") as render_preview,
        ):
            app.render_history_page(history)

        render_preview.assert_called_once_with(
            {
                "question": "Who won?",
                "answer": "Argentina won.",
                "sources": [],
            }
        )

    def test_new_question_button_returns_to_clean_ask_page(self) -> None:
        """The shared button clears either result and selects the Ask page."""
        fake_streamlit = Mock()
        fake_streamlit.session_state = {
            "page": "History",
            "selected_history_index": 0,
            "latest_preview": {"answer": "Old answer"},
        }

        with patch.object(app, "st", fake_streamlit):
            app._start_new_question()

        self.assertEqual(
            fake_streamlit.session_state,
            {
                "page": "Ask",
                "selected_history_index": None,
                "query_input": "",
            },
        )

    def test_shared_preview_renders_question_answer_and_sources(self) -> None:
        """Both new and historical results use the same preview renderer."""
        fake_streamlit = Mock()
        preview = {
            "question": "Who won?",
            "answer": "Argentina won [Source 1].",
            "sources": [
                {
                    "id": "chunk_1",
                    "content": "Argentina won the final.",
                    "metadata": {
                        "article_id": "article_1",
                        "match_id": "match_1",
                        "src": "article_1.txt",
                    },
                }
            ],
        }

        with patch.object(app, "st", fake_streamlit):
            app.render_answer_preview(preview)

        fake_streamlit.button.assert_called_once_with(
            "New Question", on_click=app._start_new_question, type="primary"
        )
        self.assertEqual(
            fake_streamlit.header.call_args_list,
            [call("Question"), call("Answer"), call("Sources")],
        )
        fake_streamlit.write.assert_any_call("Who won?")
        fake_streamlit.write.assert_any_call("Argentina won [Source 1].")
        fake_streamlit.write.assert_any_call("Argentina won the final.")


if __name__ == "__main__":
    unittest.main()
