"""Build an evidence-grounded prompt from retrieved article chunks."""


def build_prompt(
    query: str,
    retrieved_chunks: list[dict[str, object]],
) -> str:
    """Combine a user query and retrieved evidence into an augmented prompt."""
    raise NotImplementedError
