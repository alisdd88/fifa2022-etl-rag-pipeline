"""Generate an answer from semantic or structured retrieved evidence."""

import json

import ollama

from config.settings import (
    LOCAL_MODEL_NAME,
    SQL_GENERATION_PROMPT,
    STRUCTURED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)


def generate_response(
    augmented_prompt: str,
    router: str = "semantic",
    model_name: str = LOCAL_MODEL_NAME,
    *,
    sql_query: str | None = None,
    sql_result: list[dict[str, object]] | None = None,
) -> str:
    """Send an augmented prompt to the local model and return its text response.

    Args:
        augmented_prompt: Semantic augmented prompt or original structured question.
        router: Retrieval route, either ``semantic`` or ``structured``.
        model_name: Name of the model available to the local Ollama server.
        sql_query: Validated SQL used by structured retrieval.
        sql_result: Dictionary rows returned by structured retrieval.

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
    if router not in {"semantic", "structured"}:
        raise ValueError("Router must be either 'semantic' or 'structured'.")

    if router == "semantic":
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
    else:
        if not isinstance(sql_query, str) or not sql_query.strip():
            raise ValueError("Structured generation requires a non-empty SQL query.")
        if sql_result is None:
            raise ValueError("Structured generation requires an SQL result.")

        serialized_result = json.dumps(
            sql_result,
            ensure_ascii=False,
            default=str,
        )
        system_prompt = STRUCTURED_SYSTEM_PROMPT.format(
            sql_query=sql_query.strip(),
            sql_result=serialized_result,
        )
        user_prompt = SQL_GENERATION_PROMPT.format(
            user_query=augmented_prompt.strip(),
        )
        response = ollama.generate(
            model=model_name,
            prompt=user_prompt,
            system=system_prompt,
            options={"temperature": 0.2},
        )
        answer = response["response"]
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Ollama returned an empty or non-text response.")

    return answer.strip()
