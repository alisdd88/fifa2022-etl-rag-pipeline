"""Load processed articles for RAG indexing."""

import json

from config.settings import PROCESSED_DATA_DIR, PROJECT_ROOT

ARTICLES_METADATA_DIR = PROCESSED_DATA_DIR / "articles" / "metadata"


def load_articles() -> list[dict[str, str]]:
    """Load article text and identifiers from processed metadata files."""
    documents = []

    for metadata_path in sorted(ARTICLES_METADATA_DIR.glob("*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        file_path = PROJECT_ROOT / metadata["text_path"]
        content = file_path.read_text(encoding="utf-8")

        documents.append(
            {
                "article_id": metadata["article_id"],
                "match_id": metadata["match_id"],
                "src": file_path.name,
                "content": content,
            }
        )

    return documents
