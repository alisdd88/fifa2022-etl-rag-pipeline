"""Tests for chunking articles in the RAG indexing flow."""

import unittest

from src.rag.indexing.chunking import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_articles,
)


class ChunkArticlesTests(unittest.TestCase):
    """Verify chunk boundaries and metadata preservation."""

    def test_chunk_articles_splits_content_and_preserves_metadata(self) -> None:
        """Long content is split with overlap and identifying metadata."""
        documents = [
            {
                "article_id": "article_001",
                "match_id": "match_001",
                "src": "article_001.txt",
                "content": ("A" * CHUNK_SIZE) + ("B" * 50),
            },
            {
                "article_id": "article_002",
                "match_id": "match_002",
                "src": "article_002.txt",
                "content": "A short second article.",
            },
        ]

        chunks = chunk_articles(documents)

        self.assertEqual(
            [chunk["id"] for chunk in chunks],
            ["chunk_1", "chunk_2", "chunk_3"],
        )
        self.assertTrue(all(len(chunk["content"]) <= CHUNK_SIZE for chunk in chunks))
        self.assertEqual(
            chunks[0]["content"][-CHUNK_OVERLAP:],
            chunks[1]["content"][:CHUNK_OVERLAP],
        )
        self.assertEqual(
            {key: chunks[0][key] for key in ("article_id", "match_id", "src")},
            {
                "article_id": "article_001",
                "match_id": "match_001",
                "src": "article_001.txt",
            },
        )
        self.assertEqual(chunks[2]["article_id"], "article_002")
        self.assertEqual(chunks[2]["content"], "A short second article.")

    def test_chunk_articles_returns_empty_list_for_empty_input(self) -> None:
        """No input documents produce no chunks."""
        self.assertEqual(chunk_articles([]), [])


if __name__ == "__main__":
    unittest.main()
