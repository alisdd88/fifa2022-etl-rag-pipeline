"""Tests for initialization of the RAG pipeline."""

import unittest
from unittest.mock import Mock, patch

from src.rag import pipeline
from src.rag.indexing import index_state


class RagPipelineTests(unittest.TestCase):
    """Verify RAG initialization and retrieval-to-prompt coordination."""

    def test_init_pipeline_returns_ensured_article_collection(self) -> None:
        """Initialization delegates only to the article index manager."""
        collection = Mock()

        with patch.object(
            pipeline,
            "ensure_article_index",
            return_value=collection,
        ) as ensure_index:
            result = pipeline.init_pipeline()

        self.assertIs(result, collection)
        ensure_index.assert_called_once_with()

    def test_prepare_rag_context_returns_prompt_and_retrieved_evidence(self) -> None:
        """The pipeline preserves evidence after building the augmented prompt."""
        collection = Mock()
        retrieved_chunks = [
            {
                "id": "chunk_1",
                "content": "Argentina won.",
                "metadata": {
                    "article_id": "article_1",
                    "match_id": "match_1",
                    "src": "article_1.txt",
                },
                "distance": 0.1,
            }
        ]
        augmented_prompt = "Grounded prompt"

        with (
            patch.object(
                pipeline,
                "init_pipeline",
                return_value=collection,
            ) as initialize,
            patch.object(
                pipeline,
                "retrieve",
                return_value=retrieved_chunks,
            ) as retrieve,
            patch.object(
                pipeline,
                "build_prompt",
                return_value=augmented_prompt,
            ) as build_prompt,
        ):
            result = pipeline.prepare_rag_context("Who won?", top_k=2)

        initialize.assert_called_once_with()
        retrieve.assert_called_once_with(collection, "Who won?", top_k=2)
        build_prompt.assert_called_once_with("Who won?", retrieved_chunks)
        self.assertEqual(
            result,
            {
                "prompt": augmented_prompt,
                "retrieved_chunks": retrieved_chunks,
            },
        )

    def test_prepare_rag_context_uses_configured_default_top_k(self) -> None:
        """Omitting top_k uses the retrieval limit from project settings."""
        collection = Mock()

        with (
            patch.object(pipeline, "init_pipeline", return_value=collection),
            patch.object(pipeline, "retrieve", return_value=[]) as retrieve,
            patch.object(pipeline, "build_prompt", return_value="prompt"),
        ):
            pipeline.prepare_rag_context("Who won?")

        retrieve.assert_called_once_with(
            collection,
            "Who won?",
            top_k=pipeline.RAG_TOP_K,
        )

    def test_init_pipeline_connects_to_index_manager_and_returns_collection(
        self,
    ) -> None:
        """The public pipeline returns the collection selected by index state."""
        client = Mock()
        fingerprint = {"fingerprint": "unchanged"}
        collection = Mock(metadata=fingerprint)

        with (
            patch.object(index_state, "create_local_client", return_value=client),
            patch.object(
                index_state,
                "calculate_index_fingerprint",
                return_value=fingerprint,
            ),
            patch.object(
                index_state,
                "get_collection_if_exists",
                return_value=collection,
            ),
        ):
            result = pipeline.init_pipeline()

        self.assertIs(result, collection)


if __name__ == "__main__":
    unittest.main()
