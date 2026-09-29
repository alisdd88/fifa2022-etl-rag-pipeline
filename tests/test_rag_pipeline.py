"""Tests for initialization of the RAG pipeline."""

import unittest
from unittest.mock import Mock, patch

from src.rag import pipeline
from src.rag.indexing import index_state


class RagPipelineTests(unittest.TestCase):
    """Verify RAG initialization and retrieval-to-prompt coordination."""

    def test_init_pipeline_returns_ensured_article_collection(self) -> None:
        """Initialization delegates only to the article index manager."""
        collection = Mock()

        with patch.object(
            pipeline,
            "ensure_article_index",
            return_value=collection,
        ) as ensure_index:
            result = pipeline.init_pipeline()

        self.assertIs(result, collection)
        ensure_index.assert_called_once_with()

    def test_prepare_rag_context_returns_prompt_and_retrieved_evidence(self) -> None:
        """The pipeline preserves evidence after building the augmented prompt."""
        collection = Mock()
        retrieved_chunks = [
            {
                "id": "chunk_1",
                "content": "Argentina won.",
                "metadata": {
                    "article_id": "article_1",
                    "match_id": "match_1",
                    "src": "article_1.txt",
                },
                "distance": 0.1,
            }
        ]
        augmented_prompt = "Grounded prompt"

        with (
            patch.object(
                pipeline,
                "init_pipeline",
                return_value=collection,
            ) as initialize,
            patch.object(
                pipeline,
                "retrieve",
                return_value=retrieved_chunks,
            ) as retrieve,
            patch.object(
                pipeline,
                "build_prompt",
                return_value=augmented_prompt,
            ) as build_prompt,
        ):
            result = pipeline.prepare_rag_context("Who won?", top_k=2)

        initialize.assert_called_once_with()
        retrieve.assert_called_once_with(collection, "Who won?", top_k=2)
        build_prompt.assert_called_once_with("Who won?", retrieved_chunks)
        self.assertEqual(
            result,
            {
                "prompt": augmented_prompt,
                "retrieved_chunks": retrieved_chunks,
            },
        )

    def test_prepare_rag_context_uses_configured_default_top_k(self) -> None:
        """Omitting top_k uses the retrieval limit from project settings."""
        collection = Mock()

        with (
            patch.object(pipeline, "init_pipeline", return_value=collection),
            patch.object(pipeline, "retrieve", return_value=[]) as retrieve,
            patch.object(pipeline, "build_prompt", return_value="prompt"),
        ):
            pipeline.prepare_rag_context("Who won?")

        retrieve.assert_called_once_with(
            collection,
            "Who won?",
            top_k=pipeline.RAG_TOP_K,
        )

    def test_answer_query_generates_answer_and_preserves_evidence(self) -> None:
        """The end-to-end entry point sends its prompt to the local generator."""
        retrieved_chunks = [
            {
                "id": "chunk_1",
                "content": "Argentina won.",
                "metadata": {
                    "article_id": "article_1",
                    "match_id": "match_1",
                    "src": "article_1.txt",
                },
                "distance": 0.1,
            }
        ]
        prepared_context = {
            "prompt": "Retrieved evidence and user question",
            "retrieved_chunks": retrieved_chunks,
        }

        with (
            patch.object(
                pipeline,
                "prepare_rag_context",
                return_value=prepared_context,
            ) as prepare_context,
            patch.object(
                pipeline,
                "generate_response",
                return_value="Argentina won [Source 1].",
            ) as generate,
            patch.object(pipeline, "save_query_history") as save_history,
        ):
            result = pipeline.answer_query("Who won?", top_k=2)

        prepare_context.assert_called_once_with("Who won?", top_k=2)
        generate.assert_called_once_with(
            "Retrieved evidence and user question",
            router="semantic",
        )
        save_history.assert_called_once_with(
            query="Who won?",
            answer="Argentina won [Source 1].",
            sources=retrieved_chunks,
        )
        self.assertEqual(
            result,
            {
                "answer": "Argentina won [Source 1].",
                "retrieved_chunks": retrieved_chunks,
            },
        )

    def test_prepare_structured_context_generates_validates_and_executes_sql(
        self,
    ) -> None:
        """Structured preparation follows the approved SQL retrieval stages."""
        sql_query = "SELECT COUNT(*) AS match_count FROM matches"
        sql_result = [{"match_count": 3}]

        with (
            patch.object(pipeline, "generate_sql", return_value=sql_query) as generate,
            patch.object(pipeline, "validate_sql", return_value=True) as validate,
            patch.object(pipeline, "execute_sql", return_value=sql_result) as execute,
        ):
            result = pipeline.prepare_structured_context("How many matches?")

        generate.assert_called_once_with("How many matches?")
        validate.assert_called_once_with(sql_query)
        execute.assert_called_once_with(sql_query)
        self.assertEqual(
            result,
            {"sql_query": sql_query, "sql_result": sql_result},
        )

    def test_prepare_structured_context_rejects_invalid_generated_sql(self) -> None:
        """Generated SQL that fails validation never reaches PostgreSQL."""
        with (
            patch.object(pipeline, "generate_sql", return_value="DROP TABLE matches"),
            patch.object(pipeline, "validate_sql", return_value=False),
            patch.object(pipeline, "execute_sql") as execute,
            self.assertRaisesRegex(ValueError, "failed read-only validation"),
        ):
            pipeline.prepare_structured_context("Delete the matches")

        execute.assert_not_called()

    def test_answer_query_uses_structured_context_and_preserves_evidence(self) -> None:
        """The structured route passes SQL evidence to answer generation."""
        sql_query = "SELECT COUNT(*) AS match_count FROM matches"
        sql_result = [{"match_count": 3}]
        prepared_context = {
            "sql_query": sql_query,
            "sql_result": sql_result,
        }
        structured_sources = [
            {
                "id": "structured-query",
                "content": '[{"match_count": 3}]',
                "metadata": {
                    "retrieval_type": "structured",
                    "sql_query": sql_query,
                },
            }
        ]

        with (
            patch.object(
                pipeline,
                "prepare_structured_context",
                return_value=prepared_context,
            ) as prepare_context,
            patch.object(
                pipeline,
                "generate_response",
                return_value="Three matches are stored.",
            ) as generate,
            patch.object(pipeline, "save_query_history") as save_history,
        ):
            result = pipeline.answer_query(
                "How many matches?",
                router="structured",
            )

        prepare_context.assert_called_once_with("How many matches?")
        generate.assert_called_once_with(
            "How many matches?",
            router="structured",
            sql_query=sql_query,
            sql_result=sql_result,
        )
        save_history.assert_called_once_with(
            query="How many matches?",
            answer="Three matches are stored.",
            sources=structured_sources,
        )
        self.assertEqual(
            result,
            {
                "answer": "Three matches are stored.",
                "retrieved_chunks": structured_sources,
            },
        )

    def test_answer_query_rejects_unknown_router_before_retrieval(self) -> None:
        """An unsupported manual route does not start either retriever."""
        with (
            patch.object(pipeline, "prepare_rag_context") as prepare_semantic,
            patch.object(pipeline, "prepare_structured_context") as prepare_structured,
            self.assertRaisesRegex(ValueError, "Router must be either"),
        ):
            pipeline.answer_query("Question", router="hybrid")

        prepare_semantic.assert_not_called()
        prepare_structured.assert_not_called()

    def test_answer_query_does_not_save_failed_generation(self) -> None:
        """History remains unchanged when local generation fails."""
        prepared_context = {
            "prompt": "Retrieved evidence and user question",
            "retrieved_chunks": [],
        }

        with (
            patch.object(
                pipeline,
                "prepare_rag_context",
                return_value=prepared_context,
            ),
            patch.object(
                pipeline,
                "generate_response",
                side_effect=ConnectionError("Ollama unavailable"),
            ),
            patch.object(pipeline, "save_query_history") as save_history,
            self.assertRaisesRegex(ConnectionError, "Ollama unavailable"),
        ):
            pipeline.answer_query("Who won?")

        save_history.assert_not_called()

    def test_init_pipeline_connects_to_index_manager_and_returns_collection(
        self,
    ) -> None:
        """The public pipeline returns the collection selected by index state."""
        client = Mock()
        fingerprint = {"fingerprint": "unchanged"}
        collection = Mock(metadata=fingerprint)

        with (
            patch.object(index_state, "create_local_client", return_value=client),
            patch.object(
                index_state,
                "calculate_index_fingerprint",
                return_value=fingerprint,
            ),
            patch.object(
                index_state,
                "get_collection_if_exists",
                return_value=collection,
            ),
        ):
            result = pipeline.init_pipeline()

        self.assertIs(result, collection)


if __name__ == "__main__":
    unittest.main()
