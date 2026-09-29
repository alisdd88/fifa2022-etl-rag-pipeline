"""Split documents into chunks for RAG indexing."""

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_articles(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    """Split loaded articles while preserving their identifying metadata."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = []
    chunk_id = 1

    for document in documents:
        chunked_contents = text_splitter.split_text(document["content"])

        for chunked_content in chunked_contents:
            chunks.append(
                {
                    "id": f"chunk_{chunk_id}",
                    "article_id": document["article_id"],
                    "match_id": document["match_id"],
                    "src": document["src"],
                    "content": chunked_content,
                }
            )
            chunk_id += 1

    return chunks
