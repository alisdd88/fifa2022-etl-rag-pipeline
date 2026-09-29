"""Command-line entry point for asking one RAG question."""

from src.etl.utils.logging import configure_logging
from src.rag.pipeline import answer_query


def main() -> None:
    """Read one query, run the RAG pipeline, and print its answer."""
    configure_logging()
    query = input("Ask a FIFA World Cup 2022 question: ")
    result = answer_query(query)
    print(result["answer"])


if __name__ == "__main__":
    main()
