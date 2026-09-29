"""Tests for loading processed article metadata."""

import json
from unittest.mock import MagicMock

import pytest

from src.db import load_media


def _write_article_metadata(
    project_root,
    metadata_dir,
    article_id: str,
    match_id: str,
) -> None:
    """Write one processed article fixture and its referenced text file."""
    text_path = project_root / "data" / "processed" / "articles" / f"{article_id}.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text("Article text", encoding="utf-8")
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / f"{article_id}.json").write_text(
        json.dumps(
            {
                "article_id": article_id,
                "match_id": match_id,
                "source": "The Guardian",
                "article_type": "value-is-not-used",
                "text_path": text_path.relative_to(project_root).as_posix(),
            }
        ),
        encoding="utf-8",
    )


def test_read_article_rows_maps_the_correct_keys(monkeypatch, tmp_path) -> None:
    """JSON fields map to table columns and type is always article."""
    metadata_dir = tmp_path / "data" / "processed" / "articles" / "metadata"
    _write_article_metadata(tmp_path, metadata_dir, "article_002", "match_002")
    _write_article_metadata(tmp_path, metadata_dir, "article_001", "match_001")
    monkeypatch.setattr(load_media, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(load_media, "ARTICLE_METADATA_DIR", metadata_dir)

    rows = load_media._read_article_rows()

    assert rows == [
        (
            "article_001",
            "match_001",
            "The Guardian",
            "article",
            "data/processed/articles/article_001.txt",
            "data/processed/articles/metadata/article_001.json",
        ),
        (
            "article_002",
            "match_002",
            "The Guardian",
            "article",
            "data/processed/articles/article_002.txt",
            "data/processed/articles/metadata/article_002.json",
        ),
    ]


def test_read_article_rows_rejects_missing_required_key(
    monkeypatch,
    tmp_path,
) -> None:
    """A malformed processed JSON file is rejected before database insertion."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    (metadata_dir / "article.json").write_text(
        json.dumps(
            {
                "article_id": "article_001",
                "match_id": "match_001",
                "source": "The Guardian",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(load_media, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(load_media, "ARTICLE_METADATA_DIR", metadata_dir)

    with pytest.raises(ValueError, match="text_path"):
        load_media._read_article_rows()


def test_validate_article_load_compares_complete_rows() -> None:
    """Database validation checks row counts and all six column values."""
    expected_rows = [
        (
            "article_001",
            "match_001",
            "The Guardian",
            "article",
            "article.txt",
            "article.json",
        )
    ]
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = expected_rows

    count = load_media.validate_article_load(connection, expected_rows)

    assert count == 1
    connection.execute.assert_called_once()
