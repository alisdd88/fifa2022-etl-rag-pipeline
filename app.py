"""Streamlit interface for asking questions and reviewing query history."""

from typing import TypedDict

import streamlit as st

from src.etl.utils.logging import configure_logging
from src.rag.pipeline import answer_query
from src.ui.history import HistoryItem, format_history_datetime, load_query_history


class AnswerPreview(TypedDict):
    """Question, generated answer, and sources shown on the shared result page."""

    question: str
    answer: str
    sources: list[dict[str, object]]


def _start_new_question() -> None:
    """Return to a clean Ask page from either kind of answer preview."""
    st.session_state["page"] = "Ask"
    st.session_state["selected_history_index"] = None
    st.session_state["query_input"] = ""
    st.session_state.pop("latest_preview", None)


def render_answer_preview(preview: AnswerPreview) -> None:
    """Render the result page shared by new and historical answers."""
    st.button("New Question", on_click=_start_new_question, type="primary")

    st.header("Question")
    st.write(preview["question"])

    st.header("Answer")
    st.write(preview["answer"])

    st.header("Sources")
    if not preview["sources"]:
        st.write("No sources were stored for this answer.")
        return

    for source_number, source in enumerate(preview["sources"], start=1):
        metadata = source.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        label = metadata.get("src") or metadata.get("article_id")
        heading = f"Source {source_number}"
        if isinstance(label, str) and label.strip():
            heading = f"{heading}: {label.strip()}"

        st.subheader(heading)
        identifiers = [
            ("Article", metadata.get("article_id")),
            ("Match", metadata.get("match_id")),
            ("Chunk", source.get("id")),
        ]
        details = " · ".join(
            f"{name}: {value}"
            for name, value in identifiers
            if isinstance(value, str) and value.strip()
        )
        if details:
            st.caption(details)

        content = source.get("content")
        if isinstance(content, str) and content.strip():
            st.write(content.strip())


def _preview_from_history(item: HistoryItem) -> AnswerPreview:
    """Map one validated history item to the shared preview structure."""
    return {
        "question": item["query"],
        "answer": item["answer"],
        "sources": item["sources"],
    }


def render_ask_page() -> None:
    """Collect a new question and show its generated result."""
    st.title("FIFA World Cup 2022 Match Explorer")

    with st.form("question_form"):
        query = st.text_input("Ask a question", key="query_input")
        router = st.radio(
            "Retrieval method",
            ("semantic", "structured"),
            format_func=str.title,
            horizontal=True,
            key="retrieval_router",
        )
        submitted = st.form_submit_button("Get answer")

    if submitted:
        if not query.strip():
            st.warning("Enter a question before requesting an answer.")
        else:
            try:
                with st.spinner("Retrieving evidence and generating an answer..."):
                    result = answer_query(query.strip(), router=router)
            # Indexing, model loading, and Ollama can raise different library errors.
            except Exception as error:  # noqa: BLE001
                st.error(f"The answer could not be generated: {error}")
            else:
                st.session_state["latest_preview"] = {
                    "question": query.strip(),
                    "answer": result["answer"],
                    "sources": result["retrieved_chunks"],
                }

    latest_preview = st.session_state.get("latest_preview")
    if isinstance(latest_preview, dict):
        render_answer_preview(latest_preview)


def render_history_page(history: list[HistoryItem]) -> None:
    """Show history choices or the selected item through the shared preview."""
    selected_index = st.session_state.get("selected_history_index")
    if isinstance(selected_index, int) and 0 <= selected_index < len(history):
        if st.button("← Back to History"):
            st.session_state["selected_history_index"] = None
            st.rerun()
        render_answer_preview(_preview_from_history(history[selected_index]))
        return

    st.title("History")
    for index in range(len(history) - 1, -1, -1):
        item = history[index]
        if st.button(item["query"], key=f"history_{index}", use_container_width=True):
            st.session_state["selected_history_index"] = index
            st.rerun()

        created_at = item.get("created_at")
        if created_at:
            formatted_date = format_history_datetime(created_at)
            if formatted_date:
                st.caption(formatted_date)


def main() -> None:
    """Run the Streamlit application with history only when records exist."""
    st.set_page_config(page_title="FIFA World Cup 2022 Match Explorer")
    configure_logging()
    history = load_query_history()

    if history:
        page = st.sidebar.radio("Navigation", ("Ask", "History"), key="page")
    else:
        page = "Ask"
        st.session_state["page"] = page
        st.session_state["selected_history_index"] = None

    if page == "History":
        render_history_page(history)
    else:
        render_ask_page()


if __name__ == "__main__":
    main()
