"""Initialize the local RAG indexing pipeline."""

import chromadb

from src.rag.indexing.index_state import ensure_article_index


def init_pipeline() -> chromadb.Collection:
    """Ensure the article index is current and return its collection."""
    return ensure_article_index()
