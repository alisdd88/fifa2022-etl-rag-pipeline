"""Tests for Guardian article extraction."""

import json
from unittest.mock import Mock, patch

import pytest

from src.etl.extraction.articles import ARTICLE_LIMIT, MATCH_QUERIES, extract_articles


def guardian_payload(result_count: int = ARTICLE_LIMIT) -> dict:
    """Return a small valid Guardian response payload."""
    results = [
        {
            "id": f"football/article-{index}",
            "sectionName": "Football",
            "webPublicationDate": "2022-12-18T18:00:00Z",
            "webTitle": f"Match article {index}",
            "webUrl": f"https://www.theguardian.com/football/article-{index}",
            "apiUrl": f"https://content.guardianapis.com/football/article-{index}",
            "fields": {"bodyText": f"Article body {index}"},
        }
        for index in range(result_count)
    ]
    return {
        "response": {
            "status": "ok",
            "total": 10,
            "currentPage": 1,
            "pageSize": ARTICLE_LIMIT,
            "pages": 4,
            "results": results,
        }
    }


def test_extract_articles_saves_match_linked_results_without_api_key(tmp_path) -> None:
    """Each match receives one provenance-aware file containing three results."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = guardian_payload()

    with patch(
        "src.etl.extraction.articles.requests.get", return_value=response
    ) as get:
        output_paths = extract_articles(api_key="secret-key", output_dir=tmp_path)

    assert get.call_count == len(MATCH_QUERIES)
    assert len(output_paths) == len(MATCH_QUERIES)
    for query, output_path in zip(MATCH_QUERIES, output_paths, strict=True):
        assert output_path.name == f"{query['match_id']}_raw_file.json"
        record = json.loads(output_path.read_text(encoding="utf-8"))
        assert record["match_id"] == query["match_id"]
        assert len(record["articles"]) == ARTICLE_LIMIT
        assert record["source"] == "The Guardian Open Platform"
        assert "secret-key" not in output_path.read_text(encoding="utf-8")


def test_extract_articles_refuses_to_overwrite_raw_file(tmp_path) -> None:
    """Existing raw article files stop extraction before any request is sent."""
    first_match_id = MATCH_QUERIES[0]["match_id"]
    (tmp_path / f"{first_match_id}_raw_file.json").write_text("{}", encoding="utf-8")

    with (
        patch("src.etl.extraction.articles.requests.get") as get,
        pytest.raises(FileExistsError, match="already exist"),
    ):
        extract_articles(api_key="secret-key", output_dir=tmp_path)

    get.assert_not_called()


def test_extract_articles_rejects_incomplete_result_set(tmp_path) -> None:
    """A response with fewer than three results is not saved as complete raw data."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = guardian_payload(result_count=2)

    with (
        patch("src.etl.extraction.articles.requests.get", return_value=response),
        pytest.raises(ValueError, match="Expected 3"),
    ):
        extract_articles(api_key="secret-key", output_dir=tmp_path)

    assert list(tmp_path.iterdir()) == []
