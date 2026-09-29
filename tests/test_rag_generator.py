"""Focused tests for local answer generation through Ollama."""

import unittest
from unittest.mock import patch

from config.settings import SYSTEM_PROMPT
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
