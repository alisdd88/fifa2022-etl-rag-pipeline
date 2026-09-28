"""Acquire Guardian article search results for the selected matches."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from config.settings import API_KEY, ARTICLE_LIMIT, RAW_DATA_DIR

BASE_URL = "https://content.guardianapis.com/search"
OUTPUT_DIR = RAW_DATA_DIR / "articles"
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)

MATCH_QUERIES = (
    {
        "match_id": "2022_semi_finals_argentina_croatia",
        "search_terms": "Argentina Croatia",
        "from_date": "2022-12-13",
        "to_date": "2022-12-14",
    },
    {
        "match_id": "2022_semi_finals_france_morocco",
        "search_terms": "France Morocco",
        "from_date": "2022-12-14",
        "to_date": "2022-12-15",
    },
    {
        "match_id": "2022_final_argentina_france",
        "search_terms": "Argentina France World Cup final",
        "from_date": "2022-12-18",
        "to_date": "2022-12-20",
    },
)


def _request_params(query: dict[str, str], api_key: str) -> dict[str, object]:
    """Build Guardian search parameters without storing the key in metadata."""
    return {
        "q": query["search_terms"],
        "from-date": query["from_date"],
        "to-date": query["to_date"],
        "section": "football",
        "order-by": "relevance",
        "page-size": ARTICLE_LIMIT,
        "show-fields": "all",
        "api-key": api_key,
    }


def _validate_response(match_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate one Guardian response and return its article results."""
    response_data = payload.get("response")
    if not isinstance(response_data, dict) or response_data.get("status") != "ok":
        raise ValueError(f"Guardian returned an invalid response for {match_id}.")

    results = response_data.get("results")
    if not isinstance(results, list) or len(results) != ARTICLE_LIMIT:
        result_count = len(results) if isinstance(results, list) else 0
        raise ValueError(
            f"Expected {ARTICLE_LIMIT} Guardian results for {match_id}, "
            f"received {result_count}."
        )

    required_article_fields = {
        "id",
        "sectionName",
        "webPublicationDate",
        "webTitle",
        "webUrl",
        "apiUrl",
        "fields",
    }
    for index, article in enumerate(results, start=1):
        if not isinstance(article, dict):
            raise TypeError(f"Result {index} for {match_id} must be an object.")
        missing_fields = required_article_fields.difference(article)
        if missing_fields:
            raise ValueError(
                f"Result {index} for {match_id} is missing fields: "
                f"{sorted(missing_fields)}"
            )

    return results


def _fetch_match_articles(
    query: dict[str, str],
    api_key: str,
) -> dict[str, Any]:
    """Fetch and package one match's article results with provenance."""
    response = requests.get(
        BASE_URL,
        params=_request_params(query, api_key),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    articles = _validate_response(query["match_id"], payload)
    response_metadata = payload["response"]

    return {
        "match_id": query["match_id"],
        "source": "The Guardian Open Platform",
        "source_url": BASE_URL,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "query": {
            "search_terms": query["search_terms"],
            "from_date": query["from_date"],
            "to_date": query["to_date"],
            "section": "football",
            "order_by": "relevance",
            "result_limit": ARTICLE_LIMIT,
        },
        "api_metadata": {
            "status": response_metadata.get("status"),
            "total_results": response_metadata.get("total"),
            "current_page": response_metadata.get("currentPage"),
            "page_size": response_metadata.get("pageSize"),
            "pages": response_metadata.get("pages"),
        },
        "articles": articles,
    }


def extract_articles(
    api_key: str = API_KEY,
    output_dir: Path = OUTPUT_DIR,
) -> list[Path]:
    """Save three Guardian results per match as immutable raw JSON files."""
    if not api_key.strip():
        raise RuntimeError("API_KEY is not configured in the local .env file.")

    output_paths = [
        output_dir / f"{query['match_id']}_raw_file.json" for query in MATCH_QUERIES
    ]
    existing_paths = [path for path in output_paths if path.exists()]
    if existing_paths:
        raise FileExistsError(
            "Raw article files already exist: "
            + ", ".join(str(path) for path in existing_paths)
        )

    acquired_records = [
        _fetch_match_articles(query, api_key) for query in MATCH_QUERIES
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    for output_path, record in zip(output_paths, acquired_records, strict=True):
        with output_path.open("x", encoding="utf-8") as output_file:
            json.dump(record, output_file, ensure_ascii=False, indent=2)
        logger.info("Saved Guardian response to %s", output_path)

    return output_paths
