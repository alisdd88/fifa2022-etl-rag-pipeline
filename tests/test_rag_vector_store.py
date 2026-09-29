"""Tests for storing RAG chunks and embeddings in local ChromaDB."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np

from src.rag.indexing.vector_store import (
    add_chunks,
    create_collection,
    create_local_client,
    delete_collection,
    get_collection_if_exists,
    search_collection,
)

TEST_FINGERPRINT = {
    "fingerprint": "test_hash",
    "distance_metric": "cosine",
    "schema_version": 1,
}


class VectorStoreTests(unittest.TestCase):
    """Verify local persistence and aligned ChromaDB insertion."""

    def test_local_collection_persists_chunk_and_embedding(self) -> None:
        """A second client can read a chunk from the same local directory."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database_path = Path(directory)
            client = create_local_client(database_path)
            collection = create_collection(
                client,
                "test_collection",
                TEST_FINGERPRINT,
            )
            chunks = [
                {
                    "id": "chunk_1",
                    "article_id": "article_1",
                    "match_id": "match_1",
                    "src": "article_1.txt",
                    "content": "Argentina won the final.",
                }
            ]
            embeddings = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)

            count = add_chunks(collection, chunks, embeddings)
            second_client = create_local_client(database_path)
            stored_collection = get_collection_if_exists(
                second_client,
                "test_collection",
            )
            self.assertIsNotNone(stored_collection)
            stored = stored_collection.get(
                include=["documents", "metadatas", "embeddings"]
            )

            self.assertEqual(count, 1)
            self.assertEqual(stored_collection.metadata, TEST_FINGERPRINT)
            self.assertEqual(stored_collection.configuration["hnsw"]["space"], "cosine")
            self.assertEqual(stored["ids"], ["chunk_1"])
            self.assertEqual(stored["documents"], ["Argentina won the final."])
            self.assertEqual(
                stored["metadatas"],
                [
                    {
                        "article_id": "article_1",
                        "match_id": "match_1",
                        "src": "article_1.txt",
                    }
                ],
            )
            np.testing.assert_allclose(stored["embeddings"], embeddings)
            self.assertTrue((database_path / "chroma.sqlite3").is_file())

    def test_collection_lookup_and_deletion_handle_missing_collection(self) -> None:
        """Lookup returns None and deletion reports whether it removed a collection."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            client = create_local_client(Path(directory))

            self.assertIsNone(get_collection_if_exists(client, "missing_collection"))
            self.assertFalse(delete_collection(client, "missing_collection"))

            create_collection(client, "test_collection", TEST_FINGERPRINT)
            self.assertTrue(delete_collection(client, "test_collection"))
            self.assertIsNone(get_collection_if_exists(client, "test_collection"))

    def test_search_collection_formats_ranked_chroma_results(self) -> None:
        """A Chroma query is converted into retrieval result dictionaries."""
        collection = Mock()
        collection.query.return_value = {
            "ids": [["chunk_1", "chunk_2"]],
            "documents": [["First result.", "Second result."]],
            "metadatas": [
                [
                    {"match_id": "match_1", "src": "article_1.txt"},
                    {"match_id": "match_2", "src": "article_2.txt"},
                ]
            ],
            "distances": [[0.1, 0.2]],
        }
        query_embedding = np.array([0.3, 0.4], dtype=np.float32)

        results = search_collection(collection, query_embedding, top_k=2)

        collection.query.assert_called_once()
        query_arguments = collection.query.call_args.kwargs
        np.testing.assert_allclose(
            query_arguments["query_embeddings"],
            [[0.3, 0.4]],
        )
        self.assertEqual(query_arguments["n_results"], 2)
        self.assertEqual(
            query_arguments["include"],
            ["documents", "metadatas", "distances"],
        )
        self.assertEqual(
            results,
            [
                {
                    "id": "chunk_1",
                    "content": "First result.",
                    "metadata": {"match_id": "match_1", "src": "article_1.txt"},
                    "distance": 0.1,
                },
                {
                    "id": "chunk_2",
                    "content": "Second result.",
                    "metadata": {"match_id": "match_2", "src": "article_2.txt"},
                    "distance": 0.2,
                },
            ],
        )

    def test_add_chunks_rejects_misaligned_embeddings(self) -> None:
        """Every chunk must have one embedding row at the same position."""
        collection = Mock()
        chunks = [{"id": "chunk_1", "content": "text"}]

        with self.assertRaisesRegex(ValueError, "exactly one embedding"):
            add_chunks(collection, chunks, np.empty((0, 3), dtype=np.float32))

        collection.add.assert_not_called()

    def test_add_chunks_rejects_duplicate_ids(self) -> None:
        """Duplicate Chroma IDs are rejected before insertion."""
        collection = Mock()
        chunk = {
            "id": "chunk_1",
            "article_id": "article_1",
            "match_id": "match_1",
            "src": "article_1.txt",
            "content": "text",
        }
        embeddings = np.array([[0.1], [0.2]], dtype=np.float32)

        with self.assertRaisesRegex(ValueError, "must be unique"):
            add_chunks(collection, [chunk, chunk.copy()], embeddings)

        collection.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
