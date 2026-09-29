"""Tests for conditional management of the local article index."""

import unittest
from unittest.mock import Mock, patch

import numpy as np

from config.settings import RAG_COLLECTION_NAME
from src.rag.indexing import index_state


class ArticleIndexManagerTests(unittest.TestCase):
    """Verify rebuild decisions and safe index replacement order."""

    def test_ensure_article_index_reuses_unchanged_collection(self) -> None:
        """An unchanged fingerprint returns the collection without rebuilding."""
        client = Mock()
        fingerprint = {"fingerprint": "unchanged"}
        existing_collection = Mock(metadata=fingerprint)

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
                return_value=existing_collection,
            ),
            patch.object(index_state, "rebuild_index") as rebuild,
        ):
            result = index_state.ensure_article_index()

        self.assertIs(result, existing_collection)
        rebuild.assert_not_called()

    def test_ensure_article_index_builds_missing_collection(self) -> None:
        """A missing collection is built with the current fingerprint."""
        client = Mock()
        fingerprint = {"fingerprint": "current"}
        new_collection = Mock()

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
                return_value=None,
            ),
            patch.object(
                index_state,
                "rebuild_index",
                return_value=new_collection,
            ) as rebuild,
        ):
            result = index_state.ensure_article_index()

        self.assertIs(result, new_collection)
        rebuild.assert_called_once_with(client, RAG_COLLECTION_NAME, fingerprint)

    def test_ensure_article_index_rebuilds_changed_collection(self) -> None:
        """A changed fingerprint replaces the existing collection."""
        client = Mock()
        current_fingerprint = {"fingerprint": "current"}
        existing_collection = Mock(metadata={"fingerprint": "old"})
        new_collection = Mock()

        with (
            patch.object(index_state, "create_local_client", return_value=client),
            patch.object(
                index_state,
                "calculate_index_fingerprint",
                return_value=current_fingerprint,
            ),
            patch.object(
                index_state,
                "get_collection_if_exists",
                return_value=existing_collection,
            ),
            patch.object(
                index_state,
                "rebuild_index",
                return_value=new_collection,
            ) as rebuild,
        ):
            result = index_state.ensure_article_index()

        self.assertIs(result, new_collection)
        rebuild.assert_called_once_with(
            client,
            RAG_COLLECTION_NAME,
            current_fingerprint,
        )

    def test_rebuild_index_prepares_artifacts_before_deleting_collection(self) -> None:
        """Loading, chunking, and embedding finish before destructive actions."""
        client = Mock()
        collection = Mock()
        fingerprint = {"fingerprint": "current"}
        documents = [{"content": "Article text"}]
        chunks = [{"id": "chunk_1", "content": "Article text"}]
        embeddings = np.array([[0.1, 0.2]], dtype=np.float32)
        calls = []

        with (
            patch.object(
                index_state,
                "load_articles",
                side_effect=lambda: calls.append("load") or documents,
            ),
            patch.object(
                index_state,
                "chunk_articles",
                side_effect=lambda value: calls.append("chunk") or chunks,
            ),
            patch.object(
                index_state,
                "embed_chunks",
                side_effect=lambda value: calls.append("embed") or embeddings,
            ),
            patch.object(
                index_state,
                "delete_collection",
                side_effect=lambda *args: calls.append("delete"),
            ),
            patch.object(
                index_state,
                "create_collection",
                side_effect=lambda *args: calls.append("create") or collection,
            ),
            patch.object(
                index_state,
                "add_chunks",
                side_effect=lambda *args: calls.append("add") or 1,
            ),
        ):
            result = index_state.rebuild_index(client, "articles", fingerprint)

        self.assertIs(result, collection)
        self.assertEqual(calls, ["load", "chunk", "embed", "delete", "create", "add"])

    def test_rebuild_index_does_not_delete_collection_without_documents(self) -> None:
        """Invalid source data fails before the existing collection is deleted."""
        with (
            patch.object(index_state, "load_articles", return_value=[]),
            patch.object(index_state, "delete_collection") as delete,
            self.assertRaisesRegex(ValueError, "without documents"),
        ):
            index_state.rebuild_index(
                Mock(),
                "articles",
                {"fingerprint": "current"},
            )

        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
