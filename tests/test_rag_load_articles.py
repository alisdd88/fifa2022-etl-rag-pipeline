"""Tests for loading processed articles into the RAG indexing flow."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.rag.indexing import load_articles as article_loader


class LoadArticlesTests(unittest.TestCase):
    """Verify that processed metadata is joined with its article text."""

    def test_load_articles_returns_text_with_match_metadata(self) -> None:
        """A metadata JSON file produces one retrieval document."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            articles_dir = project_root / "data" / "processed" / "articles"
            metadata_dir = articles_dir / "metadata"
            metadata_dir.mkdir(parents=True)

            text_path = articles_dir / "article_test_001.txt"
            text_path.write_text("Test article content.", encoding="utf-8")
            metadata = {
                "article_id": "article_test_001",
                "match_id": "test_match",
                "text_path": "data/processed/articles/article_test_001.txt",
            }
            (metadata_dir / "article_test_001.json").write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )

            with (
                patch.object(article_loader, "PROJECT_ROOT", project_root),
                patch.object(article_loader, "ARTICLES_METADATA_DIR", metadata_dir),
            ):
                documents = article_loader.load_articles()

        self.assertEqual(
            documents,
            [
                {
                    "article_id": "article_test_001",
                    "match_id": "test_match",
                    "src": "article_test_001.txt",
                    "content": "Test article content.",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
