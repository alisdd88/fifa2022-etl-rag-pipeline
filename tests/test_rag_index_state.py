"""Tests for detecting changes to the persisted RAG index."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.rag.indexing import index_state


class IndexStateTests(unittest.TestCase):
    """Verify deterministic fingerprints and rebuild decisions."""

    def create_article_files(self, root: Path) -> tuple[Path, Path]:
        """Create one processed article and its metadata fixture."""
        metadata_dir = root / "metadata"
        metadata_dir.mkdir(parents=True)
        text_path = root / "article_001.txt"
        metadata_path = metadata_dir / "article_001.json"
        text_path.write_text("Original article text.", encoding="utf-8")
        metadata_path.write_text(
            json.dumps(
                {
                    "article_id": "article_001",
                    "match_id": "match_001",
                    "text_path": "data/processed/articles/article_001.txt",
                }
            ),
            encoding="utf-8",
        )
        return text_path, metadata_path

    def test_fingerprint_is_deterministic_and_includes_index_configuration(
        self,
    ) -> None:
        """Unchanged files and settings produce the same complete fingerprint."""
        with tempfile.TemporaryDirectory() as directory:
            articles_dir = Path(directory)
            self.create_article_files(articles_dir)

            first = index_state.calculate_index_fingerprint(articles_dir)
            second = index_state.calculate_index_fingerprint(articles_dir)

        self.assertEqual(first, second)
        self.assertEqual(first["distance_metric"], "cosine")
        self.assertEqual(first["source_file_count"], 2)
        self.assertEqual(first["schema_version"], 1)

    def test_fingerprint_changes_when_article_inputs_change(self) -> None:
        """Changes to article text or metadata each produce a new fingerprint."""
        with tempfile.TemporaryDirectory() as directory:
            articles_dir = Path(directory)
            text_path, metadata_path = self.create_article_files(articles_dir)
            original = index_state.calculate_index_fingerprint(articles_dir)

            text_path.write_text("Updated article text.", encoding="utf-8")
            changed_text = index_state.calculate_index_fingerprint(articles_dir)

            text_path.write_text("Original article text.", encoding="utf-8")
            metadata_path.write_text(
                json.dumps({"article_id": "article_001", "match_id": "match_002"}),
                encoding="utf-8",
            )
            changed_metadata = index_state.calculate_index_fingerprint(articles_dir)

        self.assertNotEqual(original["fingerprint"], changed_text["fingerprint"])
        self.assertNotEqual(original["fingerprint"], changed_metadata["fingerprint"])

    def test_fingerprint_changes_when_index_configuration_changes(self) -> None:
        """A changed chunking setting invalidates the existing index."""
        with tempfile.TemporaryDirectory() as directory:
            articles_dir = Path(directory)
            self.create_article_files(articles_dir)
            original = index_state.calculate_index_fingerprint(articles_dir)

            with patch.object(index_state, "CHUNK_SIZE", index_state.CHUNK_SIZE + 1):
                changed = index_state.calculate_index_fingerprint(articles_dir)

        self.assertNotEqual(original["fingerprint"], changed["fingerprint"])

    def test_index_needs_rebuild_compares_complete_fingerprints(self) -> None:
        """Missing or different state rebuilds; identical state does not."""
        current = {"fingerprint": "abc", "distance_metric": "cosine"}

        self.assertTrue(index_state.index_needs_rebuild(current, None))
        self.assertTrue(
            index_state.index_needs_rebuild(
                current,
                {"fingerprint": "different", "distance_metric": "cosine"},
            )
        )
        self.assertFalse(index_state.index_needs_rebuild(current, current.copy()))

    def test_fingerprint_rejects_missing_processed_articles(self) -> None:
        """An empty source directory cannot represent a usable index."""
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(FileNotFoundError, "No processed article"),
        ):
            index_state.calculate_index_fingerprint(Path(directory))


if __name__ == "__main__":
    unittest.main()
