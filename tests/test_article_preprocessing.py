"""Tests for Guardian article preprocessing."""

import json

import pytest

from src.preprocessing import articles


def guardian_article(source_id: str, title: str) -> dict:
    """Create a minimal raw Guardian article fixture."""
    return {
        "id": source_id,
        "sectionName": "Football",
        "webPublicationDate": "2022-12-18T18:00:00Z",
        "webTitle": title,
        "webUrl": f"https://www.theguardian.com/{source_id}",
        "apiUrl": f"https://content.guardianapis.com/{source_id}",
        "fields": {
            "bodyText": "First  paragraph.\nSecond café paragraph.",
            "byline": "Test Author",
            "wordcount": "6",
        },
    }


def configure_article_paths(tmp_path, monkeypatch) -> tuple:
    """Point article preprocessing at an isolated temporary data tree."""
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw" / "articles"
    processed_dir = data_dir / "processed" / "articles"
    metadata_dir = processed_dir / "metadata"
    relevant_ids_file = data_dir / "metadata" / "articles" / "relevant_ids.json"
    raw_dir.mkdir(parents=True)
    relevant_ids_file.parent.mkdir(parents=True)

    monkeypatch.setattr(articles, "DATA_DIR", data_dir)
    monkeypatch.setattr(articles, "RAW_ARTICLES_DIR", raw_dir)
    monkeypatch.setattr(articles, "PROCESSED_ARTICLES_DIR", processed_dir)
    monkeypatch.setattr(articles, "PROCESSED_METADATA_DIR", metadata_dir)
    monkeypatch.setattr(articles, "RELEVANT_IDS_FILE", relevant_ids_file)
    return raw_dir, processed_dir, metadata_dir, relevant_ids_file


def test_transform_articles_writes_selected_text_and_metadata(
    tmp_path, monkeypatch
) -> None:
    """Only approved articles are written with deterministic project IDs."""
    raw_dir, processed_dir, metadata_dir, relevant_ids_file = configure_article_paths(
        tmp_path, monkeypatch
    )
    selected_id = "football/selected"
    rejected_id = "football/rejected"
    relevant_ids_file.write_text(json.dumps([selected_id]), encoding="utf-8")
    raw_path = raw_dir / "2022_final_argentina_france_raw_file.json"
    raw_path.write_text(
        json.dumps(
            {
                "match_id": "2022_final_argentina_france",
                "articles": [
                    guardian_article(selected_id, "Selected report"),
                    guardian_article(rejected_id, "Rejected report"),
                ],
            }
        ),
        encoding="utf-8",
    )

    counts = articles.transform_articles()

    assert counts == {"evaluated": 2, "processed": 1, "skipped": 1}
    article_id = "article_2022_final_argentina_france_001"
    text_path = processed_dir / f"{article_id}.txt"
    metadata = json.loads(
        (metadata_dir / f"{article_id}.json").read_text(encoding="utf-8")
    )
    assert text_path.read_text(encoding="utf-8") == (
        "First paragraph.\n\nSecond café paragraph."
    )
    assert metadata["article_id"] == article_id
    assert metadata["match_id"] == "2022_final_argentina_france"
    assert metadata["source_article_id"] == selected_id
    assert metadata["word_count"] == 6
    assert metadata["text_path"] == f"data/processed/articles/{article_id}.txt"
    assert metadata["raw_source_path"] == (
        "data/raw/articles/2022_final_argentina_france_raw_file.json"
    )


def test_transform_articles_rejects_missing_approved_id(tmp_path, monkeypatch) -> None:
    """Every manually approved ID must occur in the raw article files."""
    raw_dir, _, _, relevant_ids_file = configure_article_paths(tmp_path, monkeypatch)
    relevant_ids_file.write_text(json.dumps(["football/missing"]), encoding="utf-8")
    (raw_dir / "2022_final_argentina_france_raw_file.json").write_text(
        json.dumps(
            {
                "match_id": "2022_final_argentina_france",
                "articles": [guardian_article("football/other", "Other report")],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Approved article IDs not found"):
        articles.transform_articles()
