"""Store article chunks and embeddings in ChromaDB."""

from pathlib import Path

import chromadb
import numpy as np
from chromadb.errors import NotFoundError

from config.settings import CHROMA_DB_DIR, RAG_DISTANCE_METRIC, RAG_TOP_K


def create_local_client(
    persist_directory: Path = CHROMA_DB_DIR,
) -> chromadb.ClientAPI:
    """Create a ChromaDB client backed by a local persistent directory."""
    return chromadb.PersistentClient(path=str(persist_directory))


def get_collection_if_exists(
    client: chromadb.ClientAPI,
    collection_name: str,
) -> chromadb.Collection | None:
    """Return an existing collection, or None when it does not exist."""
    try:
        return client.get_collection(name=collection_name)
    except NotFoundError:
        return None


def delete_collection(
    client: chromadb.ClientAPI,
    collection_name: str,
) -> bool:
    """Delete an existing collection and report whether one was deleted."""
    if get_collection_if_exists(client, collection_name) is None:
        return False
    client.delete_collection(name=collection_name)
    return True


def create_collection(
    client: chromadb.ClientAPI,
    collection_name: str,
    fingerprint: dict[str, str | int],
) -> chromadb.Collection:
    """Create a cosine-distance collection with one index fingerprint."""
    return client.create_collection(
        name=collection_name,
        configuration={"hnsw": {"space": RAG_DISTANCE_METRIC}},
        metadata=fingerprint,
        embedding_function=None,
    )


def search_collection(
    collection: chromadb.Collection, query_embedding: np.ndarray, top_k: int = RAG_TOP_K
) -> list[dict]:
    """
    Searches the collection using a query vector.
    Returns a clean list of formatted search result dictionaries.
    """
    # Perform vector similarity query
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Reformat raw Chroma results into a clean list of document records
    formatted_results = []

    documents = results["documents"][0]
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc_id, doc_text, meta, distance in zip(ids, documents, metadatas, distances):
        formatted_results.append(
            {"id": doc_id, "content": doc_text, "metadata": meta, "distance": distance}
        )

    return formatted_results


def add_chunks(
    collection: chromadb.Collection,
    chunks: list[dict[str, str]],
    embeddings: np.ndarray,
) -> int:
    """Add aligned chunks and embedding vectors to a collection."""
    if len(chunks) != len(embeddings):
        raise ValueError("Every chunk must have exactly one embedding vector.")
    if not chunks:
        return collection.count()

    documents = []
    ids = []
    metadatas = []

    for chunk in chunks:
        documents.append(chunk["content"])
        ids.append(chunk["id"])
        metadatas.append(
            {
                "article_id": chunk["article_id"],
                "match_id": chunk["match_id"],
                "src": chunk["src"],
            }
        )

    if len(ids) != len(set(ids)):
        raise ValueError("Chunk IDs must be unique within one insertion batch.")

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    return collection.count()
