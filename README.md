# Multimodal FIFA World Cup 2022 Match Explorer

This repository is being developed as a provenance-aware, match-centered ETL and RAG project.

## Current status

The ETL implementation is isolated under `src/etl/`. RAG indexing under `src/rag/` loads processed articles, creates overlapping chunks and MiniLM embeddings, and persists them in a local cosine-distance ChromaDB collection. A content-and-configuration fingerprint prevents unnecessary rebuilding. The RAG pipeline embeds a cleaned query, retrieves the nearest article chunks, and builds an evidence-grounded prompt while preserving its source chunks. Answer generation is not implemented yet.

## Planned ETL flow

```text
app.py -> run_etl() -> extract() -> transform() -> load()
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

## Pipeline backlog

- After lineups are transformed, validate that every `(match_id, player_id)` pair in processed events exists in processed lineups.
