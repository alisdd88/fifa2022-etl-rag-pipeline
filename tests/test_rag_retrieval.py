"""Tests for semantic retrieval over the article collection."""

import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.rag.retrieval import semantic_retriever


class SemanticRetrieverTests(unittest.TestCase):
    """Verify query preparation, validation, and search delegation."""

    def test_retrieve_cleans_embeds_and_searches_query(self) -> None:
        """A valid query is normalized before embedding and collection search."""
        collection = Mock()
        query_embedding = np.array([0.1, 0.2], dtype=np.float32)
        expected_results = [{"id": "chunk_1", "content": "Argentina won."}]

        with (
            patch.object(
                semantic_retriever,
                "embed_query",
                return_value=query_embedding,
            ) as embed,
            patch.object(
                semantic_retriever,
                "search",
                return_value=expected_results,
            ) as search,
        ):
            results = semantic_retriever.retrieve(
                collection,
                "  WHO   won\nthe final?  ",
                top_k=3,
            )

        embed.assert_called_once_with("who won the final?")
        search.assert_called_once_with(collection, query_embedding, top_k=3)
        self.assertIs(results, expected_results)

    def test_retrieve_rejects_invalid_query_or_top_k_before_embedding(self) -> None:
        """Invalid retrieval inputs fail without loading the embedding model."""
        collection = Mock()
        invalid_inputs = [
            ("   \n\t", 3, "Query must not be empty"),
            ("Who won?", 0, "top_k must be greater than zero"),
            ("Who won?", -1, "top_k must be greater than zero"),
        ]

        for query, top_k, message in invalid_inputs:
            with (
                self.subTest(query=query, top_k=top_k),
                patch.object(semantic_retriever, "embed_query") as embed,
            ):
                with self.assertRaisesRegex(ValueError, message):
                    semantic_retriever.retrieve(collection, query, top_k)
                embed.assert_not_called()

    def test_search_delegates_to_vector_store(self) -> None:
        """Semantic search forwards its collection, vector, and result limit."""
        collection = Mock()
        query_embedding = np.array([0.1, 0.2], dtype=np.float32)
        expected_results = [{"id": "chunk_1"}]

        with patch.object(
            semantic_retriever,
            "search_collection",
            return_value=expected_results,
        ) as search_collection:
            results = semantic_retriever.search(
                collection,
                query_embedding,
                top_k=3,
            )

        search_collection.assert_called_once_with(
            collection=collection,
            query_embedding=query_embedding,
            top_k=3,
        )
        self.assertIs(results, expected_results)


if __name__ == "__main__":
    unittest.main()
