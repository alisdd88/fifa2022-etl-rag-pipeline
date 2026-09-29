"""Create embeddings for article chunks."""

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import MODEL_NAME

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model once, when it is first needed."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_chunks(chunks: list[dict[str, str]]) -> np.ndarray:
    """Encode chunk contents into a NumPy matrix of embedding vectors."""
    chunk_contents = [chunk["content"] for chunk in chunks]
    if not chunk_contents:
        return np.empty((0, 0), dtype=np.float32)

    vectors = _get_model().encode(chunk_contents, convert_to_numpy=True)
    return np.asarray(vectors)
