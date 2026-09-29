# ETL Session Handoff

## Repository state

- Branch: `feature/etl`
- Remote tracking branch: `origin/feature/etl`
- Latest completed feature: PostgreSQL loading for processed Guardian article metadata.
- Activate the Windows environment with `.venv\Scripts\activate`.
- PostgreSQL connection settings and the Guardian API key are loaded from the ignored `.env` file.

## Completed StatsBomb work

### Extraction

`src/etl/extraction/statsbomb.py` fetches the 2022 FIFA World Cup semi-finals and final from StatsBomb competition `43`, season `106`.

Raw files:

- `data/raw/statsbomb/raw_matches.json`
- `data/raw/statsbomb/raw_events.json`
- `data/raw/statsbomb/raw_lineups.json`

### Preprocessing

`src/etl/preprocessing/statsbomb.py` creates:

- `data/processed/statsbomb/competition.csv` — 1 row
- `data/processed/statsbomb/match.csv` — 3 rows
- `data/processed/statsbomb/lineups.csv` — 147 rows
- `data/processed/statsbomb/events.csv` — 84 rows

The 84 event rows contain 13 cards, 11 match goals, and 60 paired substitution actions. Period-5 shootout conversions are not classified as match goals. Every processed event player links to a processed lineup player.

### PostgreSQL loading

The database is `fifa2022wc`. `src/etl/db/schema.py` and `src/etl/db/load_structured.py` create and load:

- `competition`
- `matches`
- `lineups`
- `events`

The tables have the approved primary keys, foreign keys, unique constraints, and checks. Event metadata is stored as `JSONB`. Loading is a transactional snapshot refresh, and every loaded value is compared with its CSV source.

The StatsBomb database load is complete and working. Do not redesign it while adding article loading unless a demonstrated requirement requires a change.

## Completed Guardian article work

### Extraction

`src/etl/extraction/articles.py` queries The Guardian Open Platform for three relevance-ranked football results per selected match.

Each match receives one immutable raw file:

```text
data/raw/articles/{match_id}_raw_file.json
```

Each file stores the canonical match ID, source and retrieval provenance, query metadata, API metadata, and three Guardian article records. The API key is never written to raw data.

`src/etl/pipeline/extract.py` includes `extract_articles()` after StatsBomb extraction.

### Manual relevance review

`scripts/review_articles.py` displays each article for human y/n review. The approved source article IDs are versioned in:

```text
data/metadata/articles/relevant_ids.json
```

Review result:

- 9 Guardian results inspected
- 8 accepted
- 1 rejected

The rejected result was a pre-match supporter-response request rather than a useful match article.

### Preprocessing

`src/etl/preprocessing/articles.py` cleans and validates the eight approved articles. `src/etl/pipeline/transform.py` now runs StatsBomb preprocessing followed by article preprocessing.

Generated article artifacts:

```text
data/processed/articles/{article_id}.txt
data/processed/articles/metadata/{article_id}.json
```

Final counts:

- 8 cleaned text files
- 8 metadata JSON files
- Argentina–France: 3 articles
- Argentina–Croatia: 3 articles
- France–Morocco: 2 articles

Article IDs are deterministic and restart at `001` for each match, for example:

```text
article_2022_final_argentina_france_001
```

Each metadata file contains exactly:

```text
article_id
match_id
source
source_article_id
article_type
title
author
publication_date
section
language
web_url
api_url
word_count
text_path
raw_source_path
```

The `match_id` values use the same canonical identifiers as the StatsBomb `matches` table. Paths are project-relative and portable. Guardian source word counts are retained.

### PostgreSQL loading

`src/etl/db/schema.py` creates a shared `metadata` table with a text primary key, a foreign key to `matches(match_id)`, source, media type, content path, and metadata path. Cleaned article bodies remain file-backed rather than being duplicated in PostgreSQL.

`src/etl/db/load_media.py` reads all processed article metadata JSON files and maps:

- `article_id` to `metadata_id`;
- `match_id` to `match_id`;
- `source` to `source`;
- the constant `article` to `type`;
- `text_path` to `file_path`;
- each JSON file's project-relative path to `metadata_path`.

The loader validates required source keys, non-empty values, unique article IDs, referenced text files, database row counts, and complete row content. It refreshes article rows in its own transaction. `src/etl/pipeline/load.py` runs structured loading first and article metadata loading second.

## Latest verification

- Full transform: 9 articles evaluated, 8 processed, and 1 skipped.
- Full PostgreSQL load: 1 competition, 3 matches, 147 lineup rows, 84 event rows, and 8 article metadata rows.
- All eight database metadata rows use `type = 'article'` and project-relative file paths.
- Tests: 16 passed.
- Focused Ruff, formatting, and `git diff --check` passed.

## Next step

Choose and approve the next small ETL component. Image and audio acquisition and preprocessing remain unimplemented.

## Known limitations

- Raw extraction is immutable. Running extraction when its target raw files already exist raises `FileExistsError` intentionally.
- The top-level ETL command is therefore suitable for a clean acquisition run, not an automatic rerun over existing raw files.
- Processed and raw data files are ignored by Git; the small relevance-selection manifest is intentionally versioned.
- Image and audio extraction/preprocessing remain placeholders and are outside the current article-loading step.

## Continuation prompt

```text
Continue the FIFA 2022 ETL work on branch feature/etl. Read AGENTS.md and handoff.md completely first. StatsBomb and Guardian article extraction, preprocessing, validation, and PostgreSQL loading are complete. Inspect the repository state, then wait for the next approved ETL component. Apply the Understanding Gate before implementing new educational core logic.
```
