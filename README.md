# Multimodal FIFA World Cup 2022 Match Explorer

This repository is being developed as a provenance-aware, match-centered ETL and RAG project.

## Current status

The ETL implementation is isolated under `src/etl/`. RAG indexing under `src/rag/` loads processed articles, creates overlapping chunks and MiniLM embeddings, and persists them in a local cosine-distance ChromaDB collection. A content-and-configuration fingerprint prevents unnecessary rebuilding. Given a query, the RAG pipeline retrieves relevant chunks, builds an evidence-grounded prompt, generates an answer with a local Ollama model, and returns the answer with its supporting chunks. A Streamlit interface supports new questions and reopens valid stored queries through one shared answer preview.

## Planned ETL flow

```text
run_etl() -> extract() -> transform() -> load()
```

Raw acquisitions belong in `data/raw/`, reproducible intermediate artifacts in `data/interim/`, normalized outputs in `data/processed/`, and provenance manifests in `data/metadata/`.

## RAG indexing flow

```text
init_pipeline() -> ensure_article_index() -> load -> chunk -> embed
                -> local cosine ChromaDB collection
```

The generated Chroma database is stored under `data/processed/chroma/` and is not committed to Git.

## RAG retrieval and prompt flow

```text
prepare_rag_context(query)
    -> ensure article index
    -> clean and validate query
    -> MiniLM query embedding
    -> cosine search in ChromaDB
    -> ranked top-k article chunks
    -> evidence-grounded prompt + preserved source chunks
```

## End-to-end RAG flow

```text
answer_query(query)
    -> prepare_rag_context(query)
    -> retrieve ranked article chunks
    -> build augmented prompt
    -> generate_response(prompt) with Ollama
    -> append successful result to data/history/query_history.json
    -> generated answer + supporting chunks
```

`answer_query()` is the public entry point that only requires a user query. Ollama must be running locally with the configured model available. Successful answers are stored as query, answer, sources, and UTC creation time for the UI; failed generations are not recorded.

To start the local interface, run:

```text
streamlit run app.py
```

The Ask page sends a question through the RAG pipeline and displays its answer and sources. If `data/history/query_history.json` contains valid records, a History navigation item lists them and opens a selected record in the same answer preview. Empty, invalid, or unreadable history is hidden rather than shown as an empty page.

## Pipeline backlog

- After lineups are transformed, validate that every `(match_id, player_id)` pair in processed events exists in processed lineups.
