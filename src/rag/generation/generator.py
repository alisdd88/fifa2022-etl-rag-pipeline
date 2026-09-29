"""Generate an answer from an augmented prompt using a local model."""

import ollama

from config.settings import LOCAL_MODEL_NAME, SYSTEM_PROMPT


def generate_response(augmented_prompt: str, model_name: str = LOCAL_MODEL_NAME) -> str:
    """Send an augmented prompt to the local model and return its text response.

    Args:
        augmented_prompt: The user question combined with retrieved evidence.
        model_name: Name of the model available to the local Ollama server.

    Returns:
        The non-empty answer text produced by the local model.

    Raises:
        ValueError: If the prompt or model name is blank.
        RuntimeError: If Ollama returns empty or non-text content.
        ollama.ResponseError: If Ollama rejects the request.
        ConnectionError: If the local Ollama server is unavailable.
    """
    if not augmented_prompt.strip():
        raise ValueError("Augmented prompt must not be empty.")
    if not model_name.strip():
        raise ValueError("Model name must not be empty.")

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": augmented_prompt,
            },
        ],
        options={
            "temperature": 0.2,  # Lower temperature reduces hallucinations in RAG
        },
    )
    answer = response["message"]["content"]
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Ollama returned an empty or non-text response.")

    return answer.strip()
