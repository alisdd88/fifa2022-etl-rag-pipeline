"""Transform approved Guardian articles into text and metadata files."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from config.settings import DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR

RAW_ARTICLES_DIR = RAW_DATA_DIR / "articles"
PROCESSED_ARTICLES_DIR = PROCESSED_DATA_DIR / "articles"
PROCESSED_METADATA_DIR = PROCESSED_ARTICLES_DIR / "metadata"
RELEVANT_IDS_FILE = DATA_DIR / "metadata" / "articles" / "relevant_ids.json"
RAW_FILE_SUFFIX = "_raw_file.json"


def clean_and_normalize(text: str) -> str:
    """Normalize article text while preserving readable paragraph breaks."""
    if not text:
        return ""

    normalized_text = unicodedata.normalize("NFC", text)
    normalized_text = re.sub(r"<[^>]+>", " ", normalized_text)
    normalized_text = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]",
        "",
        normalized_text,
    )
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in normalized_text.splitlines()
        if paragraph.strip()
    ]
    return "\n\n".join(paragraphs)


def generate_article_id(match_id: str, article_number: int) -> str:
    """Generate a deterministic project ID for one selected article."""
    if not match_id:
        raise ValueError("Article match ID must not be blank.")
    if article_number <= 0:
        raise ValueError("Article number must be greater than zero.")
    return f"article_{match_id}_{article_number:03d}"


def load_relevant_ids(path: Path = RELEVANT_IDS_FILE) -> set[str]:
    """Load and validate the manually approved Guardian article IDs."""
    if not path.is_file():
        raise FileNotFoundError(f"Relevant article IDs file not found: {path}")

    with path.open(encoding="utf-8") as input_file:
        values = json.load(input_file)

    if not isinstance(values, list) or not values:
        raise ValueError("Relevant article IDs must be a non-empty JSON list.")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Every relevant article ID must be a non-empty string.")
    if len(values) != len(set(values)):
        raise ValueError("Relevant article IDs must not contain duplicates.")
    return set(values)


def _relative_project_path(path: Path) -> str:
    """Return a portable path relative to the project root."""
    return path.relative_to(DATA_DIR.parent).as_posix()


def _load_selected_articles(
    raw_dir: Path,
    relevant_ids: set[str],
) -> tuple[list[dict[str, Any]], int]:
    """Load selected articles and construct their processed records."""
    raw_paths = sorted(raw_dir.glob(f"*{RAW_FILE_SUFFIX}"))
    if not raw_paths:
        raise FileNotFoundError(f"No raw article files found in: {raw_dir}")

    records = []
    encountered_source_ids = set()
    total_articles = 0

    for raw_path in raw_paths:
        match_id = raw_path.name.removesuffix(RAW_FILE_SUFFIX)
        with raw_path.open(encoding="utf-8") as input_file:
            payload = json.load(input_file)

        if payload.get("match_id") != match_id:
            raise ValueError(f"Raw match ID does not match filename: {raw_path.name}")
        articles = payload.get("articles")
        if not isinstance(articles, list):
            raise TypeError(f"Raw articles must be a list in: {raw_path.name}")

        total_articles += len(articles)
        article_number = 0
        for article in articles:
            source_article_id = article.get("id", "")
            if source_article_id not in relevant_ids:
                continue
            if source_article_id in encountered_source_ids:
                raise ValueError(f"Duplicate source article ID: {source_article_id}")

            fields = article.get("fields", {})
            cleaned_text = clean_and_normalize(fields.get("bodyText", ""))
            if not cleaned_text:
                raise ValueError(
                    f"Selected article has no body text: {source_article_id}"
                )

            article_number += 1
            article_id = generate_article_id(match_id, article_number)
            text_path = PROCESSED_ARTICLES_DIR / f"{article_id}.txt"
            metadata_path = PROCESSED_METADATA_DIR / f"{article_id}.json"
            metadata = {
                "article_id": article_id,
                "match_id": match_id,
                "source": "The Guardian",
                "source_article_id": source_article_id,
                "article_type": "article",
                "title": article.get("webTitle", ""),
                "author": fields.get("byline", "Unknown"),
                "publication_date": article.get("webPublicationDate", ""),
                "section": article.get("sectionName", ""),
                "language": "en",
                "web_url": article.get("webUrl", ""),
                "api_url": article.get("apiUrl", ""),
                "word_count": int(fields.get("wordcount", 0)),
                "text_path": _relative_project_path(text_path),
                "raw_source_path": _relative_project_path(raw_path),
            }
            records.append(
                {
                    "article_id": article_id,
                    "text": cleaned_text,
                    "text_path": text_path,
                    "metadata": metadata,
                    "metadata_path": metadata_path,
                }
            )
            encountered_source_ids.add(source_article_id)

    missing_ids = relevant_ids.difference(encountered_source_ids)
    if missing_ids:
        raise ValueError(f"Approved article IDs not found: {sorted(missing_ids)}")
    return records, total_articles


def transform_articles() -> dict[str, int]:
    """Write cleaned text and metadata for every approved Guardian article."""
    relevant_ids = load_relevant_ids(RELEVANT_IDS_FILE)
    records, total_articles = _load_selected_articles(
        RAW_ARTICLES_DIR,
        relevant_ids,
    )

    article_ids = [record["article_id"] for record in records]
    if len(article_ids) != len(set(article_ids)):
        raise ValueError("Generated article IDs must be unique.")

    PROCESSED_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    for record in records:
        record["text_path"].write_text(record["text"], encoding="utf-8")
        with record["metadata_path"].open("w", encoding="utf-8") as output_file:
            json.dump(record["metadata"], output_file, ensure_ascii=False, indent=2)

    return {
        "evaluated": total_articles,
        "processed": len(records),
        "skipped": total_articles - len(records),
    }
