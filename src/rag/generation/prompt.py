"""Build an evidence-grounded prompt from retrieved article chunks."""

from config.settings import RAG_PROMPT_TEMPLATE

NO_CONTEXT_MESSAGE = "No relevant article excerpts were retrieved."


def build_prompt(
    query: str,
    retrieved_chunks: list[dict[str, object]],
) -> str:
    """Combine a user query and retrieved evidence into an augmented prompt."""
    if not query.strip():
        raise ValueError("Query must not be empty.")

    context_parts = []

    for source_number, chunk in enumerate(retrieved_chunks, start=1):
        metadata = chunk.get("metadata")
        if not isinstance(metadata, dict):
            raise TypeError(f"Retrieved chunk {source_number} must contain metadata.")

        missing_chunk_fields = {"id", "content"} - chunk.keys()
        missing_metadata_fields = {"article_id", "match_id", "src"} - metadata.keys()
        missing_fields = sorted(missing_chunk_fields | missing_metadata_fields)
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise ValueError(
                f"Retrieved chunk {source_number} is missing required fields: {fields}."
            )

        context_parts.append(
            "\n".join(
                [
                    f"[Source {source_number}]",
                    f"Article ID: {metadata['article_id']}",
                    f"Source: {metadata['src']}",
                    f"Match ID: {metadata['match_id']}",
                    f"Chunk ID: {chunk['id']}",
                    "",
                    "Text:",
                    str(chunk["content"]),
                ]
            )
        )

    context = "\n\n".join(context_parts) if context_parts else NO_CONTEXT_MESSAGE

    return RAG_PROMPT_TEMPLATE.format(
        context=context,
        query=query.strip(),
    ).strip()
