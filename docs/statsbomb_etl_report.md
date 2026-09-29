# StatsBomb ETL Implementation Report

## Purpose

This stage created a small end-to-end ETL pipeline for the FIFA World Cup 2022 semi-finals and final. It extracts public StatsBomb data, transforms it into a simpler match-centered dataset, and loads the processed records into PostgreSQL.

## Pipeline Flow

```text
StatsBomb open data
    -> immutable raw JSON
    -> validated processed CSV
    -> PostgreSQL tables
    -> CSV-to-database validation
```

## 1. Extraction

The extraction stage requests the selected matches from StatsBomb and saves three raw files:

- `raw_matches.json`
- `raw_lineups.json`
- `raw_events.json`

Raw files are immutable. The pipeline refuses to overwrite them because they preserve the original acquired data.

A clean extraction produced:

| Raw dataset | Rows |
|---|---:|
| Matches | 3 |
| Lineups | 147 |
| Events | 11,764 |

## 2. Transformation

The transformation stage converts the nested raw data into four CSV tables:

| Processed file | Rows |
|---|---:|
| `competition.csv` | 1 |
| `match.csv` | 3 |
| `lineups.csv` | 147 |
| `events.csv` | 84 |

### Main transformation decisions

- Each match retains its StatsBomb ID and receives a readable project canonical ID.
- Events are limited to goals, cards, and substitution actions needed by this project.
- Six period-5 shootout conversions are not classified as match goals, so they do not inflate the official scoreline.
- Each substitution is represented by an `IN` action and an `OUT` action.
- Event-specific details are stored as valid JSON metadata.
- Lineups contain one player row per match.
- Nested lineup positions, position times, and cards were dropped because they are not needed for the project scope.
- `player_display_name` uses the player's nickname when available and otherwise uses the full name.
- Every processed event player was checked against the processed lineups.

## 3. PostgreSQL Configuration

The PostgreSQL connection is configured with a private `.env` file:

```text
DATABASE_URL=postgresql://...
```

The real `.env` file is ignored by Git. `.env.example` documents the required format without containing real credentials.

The connection code checks whether the configured database exists, creates it when necessary, and returns a Psycopg connection.

## 4. Database Schema

Four PostgreSQL tables are created:

### `competition`

- Composite primary key: `(competition_id, season_id)`
- One row represents one competition-season.

### `matches`

- Primary key: `match_id`
- `statsbomb_match_id` is unique and required.
- `(competition_id, season_id)` references `competition`.

### `lineups`

- Composite primary key: `(match_id, player_id)`
- `match_id` references `matches`.
- Jersey numbers are unique within each match and team.

### `events`

- Primary key: `event_id`
- `match_id` references `matches`.
- `(match_id, player_id)` references `lineups`.
- Allowed event types are `card`, `goal`, and `substitution`.
- Event metadata is stored as PostgreSQL `JSONB`.

## 5. Loading Strategy

The loader creates missing tables and loads them in foreign-key order:

```text
competition -> matches -> lineups -> events
```

Each load transactionally replaces the previous StatsBomb snapshot. The four tables are truncated and reloaded together. If loading or validation fails, PostgreSQL rolls back the transaction and does not leave a partial dataset.

The CSV field `canonical_id` is loaded as `match_id` in the `matches` and `lineups` tables. Decimal-looking event player IDs are normalized to integer identifiers before loading.

## 6. Validation Results

A clean end-to-end run completed successfully:

```text
extract -> transform -> load
```

The final PostgreSQL counts were:

| Database table | Rows |
|---|---:|
| `competition` | 1 |
| `matches` | 3 |
| `lineups` | 147 |
| `events` | 84 |

Final event categories were:

| Event type | Rows |
|---|---:|
| Card | 13 |
| Goal | 11 |
| Substitution | 60 |

Validation confirmed:

- every CSV row and column matched the corresponding database record;
- no match was missing its competition;
- no lineup row was missing its match;
- no event was missing its match or lineup player;
- all primary keys, foreign keys, unique constraints, and check constraints were active;
- repeated loading produced the same validated row counts;
- all automated tests passed.

## 7. Current Limitation

The full clean pipeline works from extraction through database loading. However, extraction intentionally raises `FileExistsError` when the project's raw files already exist. This protects immutable source data. The end-to-end verification therefore used temporary raw and processed directories while still running the real extraction, transformation, and loading functions.

A future orchestration improvement could explicitly separate a fresh extraction run from a rerun that starts with existing raw files. This behavior should be designed before changing the immutability rule.

## Implementation Commit

```text
a5aa284 feat: load StatsBomb data into PostgreSQL
```
