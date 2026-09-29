"""Tests for initialization of the RAG pipeline."""

import unittest
from unittest.mock import Mock, patch

from src.rag import pipeline
from src.rag.indexing import index_state


class RagPipelineTests(unittest.TestCase):
    """Verify that pipeline initialization returns the article collection."""

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
