"""Retrieve article chunks with semantic similarity search."""

import re

import chromadb
import numpy as np

from src.rag.indexing.embedding import embed_query
from src.rag.indexing.vector_store import search_collection


def search(
    collection: chromadb.Collection,
    query_embedding: np.ndarray,
    top_k: int,
) -> list[dict[str, object]]:
    """Search the article index for the top-k nearest chunks."""
    search_results = search_collection(
        collection=collection, query_embedding=query_embedding, top_k=top_k
    )

    return search_results


def retrieve(
    collection: chromadb.Collection, query: str, top_k: int
) -> list[dict[str, object]]:
    """Embed a query and return its top-k semantically similar chunks."""
    cleaned_query = re.sub(r"[\s\x00-\x1f\x7f]+", " ", query.lower()).strip()

    if not cleaned_query:
        raise ValueError("Query must not be empty.")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    query_embedding = embed_query(cleaned_query)

    results = search(collection, query_embedding, top_k=top_k)

    return results
