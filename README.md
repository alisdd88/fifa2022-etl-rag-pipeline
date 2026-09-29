# Multimodal FIFA World Cup 2022 Match Explorer

This repository is being developed as a provenance-aware, match-centered ETL and RAG project.

## Current status

The ETL implementation is isolated under `src/etl/`. RAG indexing under `src/rag/` loads processed articles, creates overlapping chunks and MiniLM embeddings, and persists them in a local cosine-distance ChromaDB collection. A content-and-configuration fingerprint prevents unnecessary rebuilding. Semantic retrieval embeds a cleaned query with the same MiniLM model and returns the nearest article chunks. Prompt construction and answer generation are not implemented yet.

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

## RAG retrieval flow

```text
query -> clean and validate -> MiniLM query embedding
      -> cosine search in ChromaDB -> ranked top-k article chunks
```

## Pipeline backlog

- After lineups are transformed, validate that every `(match_id, player_id)` pair in processed events exists in processed lineups.
