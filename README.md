# Multimodal FIFA World Cup 2022 Match Explorer

This repository is being developed as a provenance-aware, match-centered ETL and RAG project.

## Current status

The ETL package structure and entry points are scaffolded. StatsBomb extraction and match/competition preprocessing are implemented. Lineup and event preprocessing, other modalities, the database schema, and loading rules remain intentionally unimplemented until their behavior is agreed.

## Planned ETL flow

```text
app.py -> run_etl() -> extract() -> transform() -> load()
```

Raw acquisitions belong in `data/raw/`, reproducible intermediate artifacts in `data/interim/`, normalized outputs in `data/processed/`, and provenance manifests in `data/metadata/`.
