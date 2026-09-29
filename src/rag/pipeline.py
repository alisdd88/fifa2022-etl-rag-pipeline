"""Coordinate indexing, retrieval, and prompt construction for RAG."""

from typing import TypedDict

import chromadb

from config.settings import RAG_TOP_K
from src.rag.generation.prompt import build_prompt
from src.rag.indexing.index_state import ensure_article_index
from src.rag.retrieval.semantic_retriever import retrieve


class PreparedRagContext(TypedDict):
    """Prompt and supporting evidence prepared for answer generation."""

    prompt: str
    retrieved_chunks: list[dict[str, object]]


def init_pipeline() -> chromadb.Collection:
    """Ensure the article index is current and return its collection."""
    return ensure_article_index()


def prepare_rag_context(
    query: str,
    top_k: int = RAG_TOP_K,
) -> PreparedRagContext:
    """Retrieve evidence and build the augmented prompt for one query."""
    collection = init_pipeline()
    retrieved_chunks = retrieve(collection, query, top_k=top_k)
    prompt = build_prompt(query, retrieved_chunks)

    return {
        "prompt": prompt,
        "retrieved_chunks": retrieved_chunks,
    }
