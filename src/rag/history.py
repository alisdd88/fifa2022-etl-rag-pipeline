"""Persist successful RAG queries for the user interface."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from config.settings import QUERY_HISTORY_PATH


class QueryHistoryRecord(TypedDict):
    """One successfully generated answer and its supporting sources."""

    query: str
    answer: str
    sources: list[dict[str, object]]
    created_at: str


def save_query_history(
    query: str,
    answer: str,
    sources: list[dict[str, object]],
    history_path: Path = QUERY_HISTORY_PATH,
) -> QueryHistoryRecord:
    """Append one successful query result to the JSON history file."""
    output_path = Path(history_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        history = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            raise ValueError("Query history must contain a JSON list.")
    else:
        history = []

    record: QueryHistoryRecord = {
        "query": query.strip(),
        "answer": answer.strip(),
        "sources": sources,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    history.append(record)

    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)

    return record
