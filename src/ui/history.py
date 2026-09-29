"""Safely load existing RAG query history for the user interface."""

import json
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from config.settings import QUERY_HISTORY_PATH


class HistoryItem(TypedDict):
    """A validated historical answer that can be shown in the UI."""

    query: str
    answer: str
    sources: list[dict[str, object]]
    created_at: NotRequired[str]


def load_query_history(history_path: Path = QUERY_HISTORY_PATH) -> list[HistoryItem]:
    """Return valid records from the existing history file, or an empty list."""
    try:
        raw_history = json.loads(Path(history_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []

    if not isinstance(raw_history, list):
        return []

    valid_items: list[HistoryItem] = []
    for record in raw_history:
        if not isinstance(record, dict):
            continue

        query = record.get("query")
        answer = record.get("answer")
        sources = record.get("sources")
        if (
            not isinstance(query, str)
            or not query.strip()
            or not isinstance(answer, str)
            or not answer.strip()
            or not isinstance(sources, list)
            or not all(isinstance(source, dict) for source in sources)
        ):
            continue

        item: HistoryItem = {
            "query": query.strip(),
            "answer": answer.strip(),
            "sources": sources,
        }
        created_at = record.get("created_at")
        if isinstance(created_at, str) and created_at.strip():
            item["created_at"] = created_at.strip()
        valid_items.append(item)

    return valid_items


def format_history_datetime(value: str) -> str | None:
    """Format an ISO history timestamp for display, if it is valid."""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    formatted = timestamp.strftime("%b %d, %Y at %H:%M")
    timezone_name = timestamp.tzname()
    return f"{formatted} {timezone_name}" if timezone_name else formatted
