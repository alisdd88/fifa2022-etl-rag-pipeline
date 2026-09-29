"""Tests for embedding chunks in the RAG indexing flow."""

import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.rag.indexing import embedding


class EmbedChunksTests(unittest.TestCase):
    """Verify embedding inputs, outputs, and empty-input behavior."""

    def test_embed_chunks_encodes_content_in_input_order(self) -> None:
        """Chunk content is encoded in order and returned as a NumPy matrix."""
        chunks = [
            {"id": "chunk_1", "content": "First chunk."},
            {"id": "chunk_2", "content": "Second chunk."},
        ]
        expected_vectors = np.array(
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            dtype=np.float32,
        )
        model = Mock()
        model.encode.return_value = expected_vectors

        with patch.object(embedding, "_get_model", return_value=model):
            vectors = embedding.embed_chunks(chunks)

        model.encode.assert_called_once_with(
            ["First chunk.", "Second chunk."],
            convert_to_numpy=True,
        )
        np.testing.assert_array_equal(vectors, expected_vectors)

    def test_embed_query_encodes_one_query_as_numpy_vector(self) -> None:
        """A query uses the shared model and returns one embedding vector."""
        expected_vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        model = Mock()
        model.encode.return_value = expected_vector

        with patch.object(embedding, "_get_model", return_value=model):
            vector = embedding.embed_query("Who won the final?")

        model.encode.assert_called_once_with(
            "Who won the final?",
            convert_to_numpy=True,
        )
        np.testing.assert_array_equal(vector, expected_vector)

    def test_embed_chunks_does_not_load_model_for_empty_input(self) -> None:
        """An empty chunk list returns an empty matrix without model loading."""
        with patch.object(embedding, "_get_model") as get_model:
            vectors = embedding.embed_chunks([])

        get_model.assert_not_called()
        self.assertEqual(vectors.shape, (0, 0))
        self.assertEqual(vectors.dtype, np.float32)

    def test_get_model_loads_configured_model_only_once(self) -> None:
        """Repeated embedding calls can reuse one model instance."""
        model = Mock()
        with (
            patch.object(embedding, "_model", None),
            patch.object(
                embedding,
                "SentenceTransformer",
                return_value=model,
            ) as model_factory,
        ):
            first_model = embedding._get_model()
            second_model = embedding._get_model()

        self.assertIs(first_model, model)
        self.assertIs(second_model, model)
        model_factory.assert_called_once_with(embedding.MODEL_NAME)


if __name__ == "__main__":
    unittest.main()
