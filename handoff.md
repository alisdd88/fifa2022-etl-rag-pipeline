# ETL Session Handoff

## Repository state

- Branch: `feature/etl`
- Remote tracking branch: `origin/feature/etl`
- StatsBomb lineup preprocessing is implemented and verified.
- Activate the environment on Windows with `.venv\Scripts\activate`.

## Completed StatsBomb work

### Extraction

`src/extraction/statsbomb.py` fetches the 2022 FIFA World Cup semi-finals and final using StatsBomb competition ID `43` and season ID `106`.

`src/pipeline/extract.py` writes immutable raw JSON files:

- `data/raw/statsbomb/raw_matches.json`
- `data/raw/statsbomb/raw_events.json`
- `data/raw/statsbomb/raw_lineups.json`

These generated files are ignored by Git.

### Match and competition preprocessing

`transform_matches()` in `src/preprocessing/statsbomb.py` creates:

- `data/processed/statsbomb/match.csv` — 3 rows
- `data/processed/statsbomb/competition.csv` — 1 row

The match table preserves `statsbomb_match_id` and contains a project identifier named `canonical_id`.

### Event preprocessing

`transform_events()` and `process_events()` create:

- `data/processed/statsbomb/events.csv` — 84 rows

Final event counts:

- 60 substitution actions: 30 paired `IN`/`OUT` substitutions
- 13 cards
- 11 match goals

Six period-5 shootout conversions are excluded from `event_type="goal"` so they do not inflate match scorelines. They remain in raw data. Event metadata is valid JSON text. Processed events use `match_id` for the canonical project match identifier and retain StatsBomb source identifiers.

### Lineup preprocessing

`transform_lineups()` creates:

- `data/processed/statsbomb/lineups.csv` — 147 rows

The processed table contains one player per match, drops nested cards and position data, preserves nullable player nicknames, and creates `player_display_name` from the nickname with a full-name fallback. Each row retains `statsbomb_match_id` and links to the project `canonical_id`.

## Verification completed

- Required event categories passed.
- Required event fields contained no nulls.
- Event IDs were unique.
- Temporal ranges and timestamp presence passed.
- Every event linked to one of the three selected matches.
- Every substitution reference appeared exactly twice: one `IN` and one `OUT` action.
- Lineups contain no duplicate match/player or match/team/jersey combinations.
- All 69 distinct event match/player pairs are present in processed lineups.
- The full `transform()` stage completed successfully and regenerated all four processed CSV files.
- Tests, focused Ruff checks, formatting, compilation, and `git diff --check` passed. Full-repository Ruff still reports existing placeholder `pass` statements in unfinished modules.

## Next step: loading

`src/pipeline/load.py` and the modules under `src/db/` are placeholders. Before implementation, agree on the small relational schema, database location, table keys, foreign keys, load order, and rerun behavior. The loading design is educational core logic and must pass the Understanding Gate before implementation.

## Known pipeline limitations

- `src/pipeline/load.py` is still a placeholder.
- Running extraction again against existing raw files raises `FileExistsError` intentionally because raw data is immutable.
- The complete ETL application is therefore not yet designed as a rerunnable command.

## Continuation prompt

```text
Continue the FIFA 2022 ETL work on branch feature/etl. Read AGENTS.md and handoff.md first. StatsBomb extraction and preprocessing are complete for matches, competition, key events, and lineups. Begin by reviewing the processed CSV schemas and the placeholder loading modules, then explain and recommend a small SQLite loading design. Apply the Understanding Gate before implementing database schema or loading logic.
```
