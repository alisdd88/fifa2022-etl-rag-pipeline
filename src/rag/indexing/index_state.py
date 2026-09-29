"""Detect whether the persisted RAG index needs to be rebuilt."""

import hashlib
import json
from pathlib import Path
from typing import TypeAlias

import chromadb

from config.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MODEL_NAME,
    PROCESSED_DATA_DIR,
    RAG_COLLECTION_NAME,
    RAG_DISTANCE_METRIC,
    RAG_INDEX_SCHEMA_VERSION,
)
from src.rag.indexing.chunking import chunk_articles
from src.rag.indexing.embedding import embed_chunks
from src.rag.indexing.load_articles import load_articles
from src.rag.indexing.vector_store import (
    add_chunks,
    create_collection,
    create_local_client,
    delete_collection,
    get_collection_if_exists,
)

Fingerprint: TypeAlias = dict[str, str | int]
ARTICLES_DIR = PROCESSED_DATA_DIR / "articles"
INDEXED_FILE_SUFFIXES = {".json", ".txt"}


def calculate_index_fingerprint(
    articles_dir: Path = ARTICLES_DIR,
    collection_name: str = RAG_COLLECTION_NAME,
) -> Fingerprint:
    """Hash article files and every configuration value affecting the index."""
    source_paths = sorted(
        path
        for path in articles_dir.rglob("*")
        if path.is_file() and path.suffix in INDEXED_FILE_SUFFIXES
    )
    if not source_paths:
        raise FileNotFoundError(f"No processed article files found in: {articles_dir}")

    config_payload: Fingerprint = {
        "embedding_model": MODEL_NAME,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "collection_name": collection_name,
        "distance_metric": RAG_DISTANCE_METRIC,
        "schema_version": RAG_INDEX_SCHEMA_VERSION,
        "source_file_count": len(source_paths),
    }
    hasher = hashlib.sha256(json.dumps(config_payload, sort_keys=True).encode("utf-8"))

    for source_path in source_paths:
        relative_path = source_path.relative_to(articles_dir).as_posix()
        hasher.update(relative_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(source_path.read_bytes())
        hasher.update(b"\0")

    return {"fingerprint": hasher.hexdigest(), **config_payload}


def index_needs_rebuild(
    current_fingerprint: Fingerprint,
    stored_fingerprint: Fingerprint | None,
) -> bool:
    """Return whether the persisted index differs from its current inputs."""
    if stored_fingerprint is None:
        return True
    return current_fingerprint != stored_fingerprint


def rebuild_index(
    client: chromadb.ClientAPI,
    collection_name: str,
    fingerprint: Fingerprint,
) -> chromadb.Collection:
    """Build artifacts, replace the old collection, and return the new one."""
    documents = load_articles()
    if not documents:
        raise ValueError("Cannot build the article index without documents.")

    chunks = chunk_articles(documents)
    if not chunks:
        raise ValueError("Cannot build the article index without chunks.")

    embeddings = embed_chunks(chunks)

    delete_collection(client, collection_name)
    collection = create_collection(client, collection_name, fingerprint)
    stored_count = add_chunks(collection, chunks, embeddings)
    if stored_count != len(chunks):
        raise ValueError(
            f"ChromaDB stored {stored_count} chunks; expected {len(chunks)}."
        )
    return collection


def ensure_article_index() -> chromadb.Collection:
    """Return the current local article index, rebuilding it only when required."""
    client = create_local_client()
    current_fingerprint = calculate_index_fingerprint()
    collection = get_collection_if_exists(client, RAG_COLLECTION_NAME)

    if collection is not None and not index_needs_rebuild(
        current_fingerprint,
        collection.metadata,
    ):
        return collection

    return rebuild_index(
        client,
        RAG_COLLECTION_NAME,
        current_fingerprint,
    )
