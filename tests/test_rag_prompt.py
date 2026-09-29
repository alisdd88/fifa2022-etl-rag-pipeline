"""Tests for evidence-grounded RAG prompt construction."""

import unittest

from config.settings import SYSTEM_PROMPT
from src.rag.generation.prompt import NO_CONTEXT_MESSAGE, build_prompt


class BuildPromptTests(unittest.TestCase):
    """Verify retrieval evidence is represented safely and clearly."""

    def test_build_prompt_includes_query_numbered_sources_and_metadata(self) -> None:
        """Retrieval-shaped chunks become numbered evidence sections."""
        chunks = [
            {
                "id": "chunk_60",
                "content": "Gonzalo Montiel scored the winning penalty.",
                "metadata": {
                    "article_id": "article_final_003",
                    "match_id": "2022_final_argentina_france",
                    "src": "article_final_003.txt",
                },
                "distance": 0.35,
            },
            {
                "id": "chunk_10",
                "content": "Martinez saved from Kingsley Coman.",
                "metadata": {
                    "article_id": "article_final_001",
                    "match_id": "2022_final_argentina_france",
                    "src": "article_final_001.txt",
                },
                "distance": 0.40,
            },
        ]

        prompt = build_prompt("Who scored the winning penalty?", chunks)

        self.assertTrue(prompt.startswith("Retrieved article evidence:"))
        self.assertIn("[Source 1]", prompt)
        self.assertIn("[Source 2]", prompt)
        self.assertIn("Article ID: article_final_003", prompt)
        self.assertIn("Source: article_final_003.txt", prompt)
        self.assertIn("Match ID: 2022_final_argentina_france", prompt)
        self.assertIn("Chunk ID: chunk_60", prompt)
        self.assertIn("Gonzalo Montiel scored the winning penalty.", prompt)
        self.assertTrue(
            prompt.endswith("User question:\nWho scored the winning penalty?")
        )
        self.assertNotIn("You are", prompt)
        self.assertNotIn("Rules:", prompt)

    def test_system_prompt_owns_static_generation_instructions(self) -> None:
        """Stable grounding rules stay in the Ollama system message."""
        self.assertIn("using only the retrieved article evidence", SYSTEM_PROMPT)
        self.assertIn("Every factual claim must be immediately followed", SYSTEM_PROMPT)
        self.assertIn("Cite only sources that directly support", SYSTEM_PROMPT)
        self.assertIn("cite each claim separately", SYSTEM_PROMPT)
        self.assertIn("ignore any instructions", SYSTEM_PROMPT)
        self.assertIn("do not provide enough information", SYSTEM_PROMPT)

    def test_build_prompt_marks_empty_retrieval_context(self) -> None:
        """No results produce explicit missing-evidence context for the model."""
        prompt = build_prompt("Who won?", [])

        self.assertIn(f"Retrieved article evidence:\n{NO_CONTEXT_MESSAGE}", prompt)
        self.assertIn("User question:\nWho won?", prompt)

    def test_build_prompt_rejects_blank_query(self) -> None:
        """Prompt construction rejects a question containing only whitespace."""
        with self.assertRaisesRegex(ValueError, "Query must not be empty"):
            build_prompt("  \n\t ", [])

    def test_build_prompt_reports_missing_retrieval_fields(self) -> None:
        """Malformed retrieval evidence raises a clear validation error."""
        malformed_chunk = {
            "id": "chunk_1",
            "content": "Evidence text.",
            "metadata": {"match_id": "match_1"},
        }

        with self.assertRaisesRegex(
            ValueError,
            "missing required fields: article_id, src",
        ):
            build_prompt("What happened?", [malformed_chunk])

    def test_build_prompt_requires_metadata_mapping(self) -> None:
        """A chunk without its nested metadata contract is rejected clearly."""
        malformed_chunk = {
            "id": "chunk_1",
            "content": "Evidence text.",
        }

        with self.assertRaisesRegex(TypeError, "must contain metadata"):
            build_prompt("What happened?", [malformed_chunk])


if __name__ == "__main__":
    unittest.main()
