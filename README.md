# Multimodal FIFA World Cup 2022 Match Explorer

This repository is being developed as a provenance-aware, match-centered ETL and RAG project.

## Current status

The ETL implementation is isolated under `src/etl/`. RAG indexing under `src/rag/` loads processed articles, creates overlapping chunks and MiniLM embeddings, and persists them in a local cosine-distance ChromaDB collection. A content-and-configuration fingerprint prevents unnecessary rebuilding. Given a query, the RAG pipeline can manually route to semantic article retrieval or structured PostgreSQL retrieval. It generates an evidence-grounded answer with a local Ollama model and returns the answer with its supporting evidence. A Streamlit interface supports new questions and reopens valid stored queries through one shared answer preview.

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
answer_query(query, router="semantic")
    -> prepare_rag_context(query)
    -> retrieve ranked article chunks
    -> build augmented prompt
    -> generate semantic answer with Ollama

answer_query(query, router="structured")
    -> generate_sql(query)
    -> validate_sql(sql_query)
    -> execute_sql(sql_query) in a read-only PostgreSQL transaction
    -> generate structured answer from the SQL rows with Ollama

successful route
    -> append query, answer, and evidence to data/history/query_history.json
    -> generated answer + supporting evidence
```

`answer_query()` is the public entry point. Routing is manual and defaults to `semantic`; pass `router="structured"` for database questions. Ollama must be running locally with the configured model available, and the structured route also requires the configured PostgreSQL database. Successful answers are stored as query, answer, sources, and UTC creation time for the UI; failed generations are not recorded.

## Run the UI

Start PostgreSQL and Ollama with `llama3.2`, then run:

```text
streamlit run app.py
```

Open the displayed local URL, choose **Semantic** or **Structured**, enter a question, and select **Get answer**. If valid query history exists, the History page opens saved answers in the same preview.

## Pipeline backlog

- After lineups are transformed, validate that every `(match_id, player_id)` pair in processed events exists in processed lineups.
