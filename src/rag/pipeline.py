"""Coordinate indexing, retrieval, prompt construction, and generation."""

import json
from typing import TypedDict

import chromadb

from config.settings import RAG_TOP_K
from src.rag.generation.generator import generate_response
from src.rag.generation.prompt import build_prompt
from src.rag.history import save_query_history
from src.rag.indexing.index_state import ensure_article_index
from src.rag.retrieval.semantic_retriever import retrieve
from src.rag.retrieval.structured_retriever import (
    execute_sql,
    generate_sql,
    validate_sql,
)


class PreparedRagContext(TypedDict):
    """Prompt and supporting evidence prepared for answer generation."""

    prompt: str
    retrieved_chunks: list[dict[str, object]]


class PreparedStructuredContext(TypedDict):
    """Validated SQL and rows prepared for structured answer generation."""

    sql_query: str
    sql_result: list[dict[str, object]]


class GeneratedRagResponse(TypedDict):
    """Generated answer and the evidence used to produce it."""

    answer: str
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


def prepare_structured_context(query: str) -> PreparedStructuredContext:
    """Generate, validate, and execute SQL for one structured question."""
    sql_query = generate_sql(query)
    if not validate_sql(sql_query):
        raise ValueError("Generated SQL failed read-only validation.")

    return {
        "sql_query": sql_query,
        "sql_result": execute_sql(sql_query),
    }


def _build_structured_sources(
    prepared_context: PreparedStructuredContext,
) -> list[dict[str, object]]:
    """Represent structured evidence in the existing history and UI contract."""
    return [
        {
            "id": "structured-query",
            "content": json.dumps(
                prepared_context["sql_result"],
                ensure_ascii=False,
                default=str,
            ),
            "metadata": {
                "retrieval_type": "structured",
                "sql_query": prepared_context["sql_query"],
            },
        }
    ]


def answer_query(
    query: str,
    router: str = "semantic",
    top_k: int = RAG_TOP_K,
) -> GeneratedRagResponse:
    """Generate an answer through the manually selected retrieval route."""
    if router == "semantic":
        prepared_context = prepare_rag_context(query, top_k=top_k)
        answer = generate_response(
            prepared_context["prompt"],
            router=router,
        )
        sources = prepared_context["retrieved_chunks"]
    elif router == "structured":
        structured_context = prepare_structured_context(query)
        answer = generate_response(
            query,
            router=router,
            sql_query=structured_context["sql_query"],
            sql_result=structured_context["sql_result"],
        )
        sources = _build_structured_sources(structured_context)
    else:
        raise ValueError("Router must be either 'semantic' or 'structured'.")

    save_query_history(
        query=query,
        answer=answer,
        sources=sources,
    )

    return {
        "answer": answer,
        "retrieved_chunks": sources,
    }
