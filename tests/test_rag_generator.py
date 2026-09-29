"""Focused tests for local answer generation through Ollama."""

import unittest
from unittest.mock import patch

from config.settings import (
    SQL_GENERATION_PROMPT,
    STRUCTURED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from src.rag.generation import generator


class GenerateResponseTests(unittest.TestCase):
    """Verify the generator contract without running a local model."""

    def test_generate_response_sends_system_and_augmented_prompts(self) -> None:
        """The configured model receives separate system and user messages."""
        with patch.object(
            generator.ollama,
            "chat",
            return_value={"message": {"content": " Argentina won [Source 1]. "}},
        ) as chat:
            answer = generator.generate_response(
                "Retrieved evidence and question",
                model_name="test-model",
            )

        self.assertEqual(answer, "Argentina won [Source 1].")
        chat.assert_called_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Retrieved evidence and question",
                },
            ],
            options={"temperature": 0.2},
        )

    def test_generate_structured_response_uses_sql_evidence(self) -> None:
        """Structured generation receives the question and serialized SQL rows."""
        sql_query = "SELECT COUNT(*) AS match_count FROM matches"
        sql_result = [{"match_count": 3}]
        expected_system_prompt = STRUCTURED_SYSTEM_PROMPT.format(
            sql_query=sql_query,
            sql_result='[{"match_count": 3}]',
        )
        expected_user_prompt = SQL_GENERATION_PROMPT.format(
            user_query="How many matches are stored?",
        )

        with (
            patch.object(generator.ollama, "chat") as chat,
            patch.object(
                generator.ollama,
                "generate",
                return_value={"response": " Three matches are stored. "},
            ) as generate,
        ):
            answer = generator.generate_response(
                "How many matches are stored?",
                router="structured",
                model_name="test-model",
                sql_query=sql_query,
                sql_result=sql_result,
            )

        self.assertEqual(answer, "Three matches are stored.")
        chat.assert_not_called()
        generate.assert_called_once_with(
            model="test-model",
            prompt=expected_user_prompt,
            system=expected_system_prompt,
            options={"temperature": 0.2},
        )

    def test_generate_structured_response_requires_sql_evidence(self) -> None:
        """Missing SQL or result data fails before calling Ollama."""
        invalid_inputs = (
            {"sql_query": None, "sql_result": []},
            {"sql_query": "  ", "sql_result": []},
            {"sql_query": "SELECT 1", "sql_result": None},
        )

        for inputs in invalid_inputs:
            with (
                self.subTest(inputs=inputs),
                patch.object(generator.ollama, "generate") as generate,
                self.assertRaises(ValueError),
            ):
                generator.generate_response(
                    "Question",
                    router="structured",
                    model_name="test-model",
                    **inputs,
                )

            generate.assert_not_called()

    def test_generate_response_rejects_unknown_router(self) -> None:
        """Only implemented retrieval routes may reach Ollama."""
        with (
            patch.object(generator.ollama, "chat") as chat,
            patch.object(generator.ollama, "generate") as generate,
            self.assertRaisesRegex(ValueError, "Router must be either"),
        ):
            generator.generate_response(
                "Question",
                router="hybrid",
                model_name="test-model",
            )

        chat.assert_not_called()
        generate.assert_not_called()

    def test_generate_response_rejects_blank_prompt_without_calling_ollama(
        self,
    ) -> None:
        """An empty prompt fails before making a model request."""
        with (
            patch.object(generator.ollama, "chat") as chat,
            self.assertRaisesRegex(ValueError, "prompt must not be empty"),
        ):
            generator.generate_response("  \n ", model_name="test-model")

        chat.assert_not_called()

    def test_generate_response_rejects_blank_model_name(self) -> None:
        """A model must be selected before making an Ollama request."""
        with (
            patch.object(generator.ollama, "chat") as chat,
            self.assertRaisesRegex(ValueError, "Model name must not be empty"),
        ):
            generator.generate_response("prompt", model_name="  ")

        chat.assert_not_called()

    def test_generate_response_rejects_empty_model_output(self) -> None:
        """An empty Ollama response is not returned as a valid answer."""
        with (
            patch.object(
                generator.ollama,
                "chat",
                return_value={"message": {"content": "  "}},
            ),
            self.assertRaisesRegex(RuntimeError, "empty or non-text"),
        ):
            generator.generate_response("prompt", model_name="test-model")


if __name__ == "__main__":
    unittest.main()
