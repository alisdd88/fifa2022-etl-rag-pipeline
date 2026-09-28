"""PostgreSQL schema for processed StatsBomb records."""

import psycopg

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS competition (
        competition_id BIGINT NOT NULL,
        competition_name TEXT,
        competition_country_name TEXT,
        competition TEXT,
        season_id BIGINT NOT NULL,
        season INTEGER,
        PRIMARY KEY (competition_id, season_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        statsbomb_match_id BIGINT UNIQUE NOT NULL,
        match_date DATE,
        kick_off TIME(3),
        home_score SMALLINT CHECK (home_score >= 0),
        away_score SMALLINT CHECK (away_score >= 0),
        match_status TEXT,
        match_week INTEGER,
        competition_id BIGINT NOT NULL,
        competition_stage_id BIGINT,
        competition_stage TEXT,
        season_id BIGINT NOT NULL,
        home_team_id BIGINT,
        home_team TEXT,
        home_team_country_id BIGINT,
        home_team_country_name TEXT,
        away_team_id BIGINT,
        away_team TEXT,
        away_team_country_id BIGINT,
        away_team_country_name TEXT,
        stadium_id BIGINT,
        stadium TEXT,
        stadium_country_id BIGINT,
        stadium_country_name TEXT,
        referee_id BIGINT,
        referee TEXT,
        referee_country_id BIGINT,
        referee_country_name TEXT,
        home_managers TEXT,
        away_managers TEXT,
        home_manager_id BIGINT,
        home_manager_name TEXT,
        home_manager_dob DATE,
        home_manager_country_id BIGINT,
        home_manager_country_name TEXT,
        away_manager_id BIGINT,
        away_manager_name TEXT,
        away_manager_dob DATE,
        away_manager_country_id BIGINT,
        away_manager_country_name TEXT,
        data_version TEXT,
        shot_fidelity_version INTEGER,
        xy_fidelity_version INTEGER,
        FOREIGN KEY (competition_id, season_id)
            REFERENCES competition (competition_id, season_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lineups (
        match_id TEXT NOT NULL,
        statsbomb_match_id BIGINT NOT NULL,
        player_id BIGINT NOT NULL,
        player_name TEXT NOT NULL,
        player_nickname TEXT,
        player_display_name TEXT NOT NULL,
        jersey_number INTEGER NOT NULL CHECK (jersey_number > 0),
        country TEXT NOT NULL,
        team TEXT NOT NULL,
        PRIMARY KEY (match_id, player_id),
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        UNIQUE (match_id, team, jersey_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        statsbomb_match_id BIGINT NOT NULL,
        statsbomb_event_id UUID NOT NULL,
        statsbomb_event_index INTEGER NOT NULL,
        period SMALLINT NOT NULL CHECK (period > 0),
        minute INTEGER NOT NULL CHECK (minute >= 0),
        second SMALLINT NOT NULL CHECK (second BETWEEN 0 AND 59),
        timestamp TIME(3) NOT NULL,
        duration DOUBLE PRECISION,
        type TEXT NOT NULL,
        player_id BIGINT NOT NULL,
        team_id BIGINT NOT NULL,
        team TEXT NOT NULL,
        player TEXT NOT NULL,
        match_id TEXT NOT NULL,
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL
            CHECK (event_type IN ('card', 'goal', 'substitution')),
        metadata JSONB NOT NULL,
        FOREIGN KEY (match_id) REFERENCES matches (match_id),
        FOREIGN KEY (match_id, player_id)
            REFERENCES lineups (match_id, player_id)
    )
    """,
)


def create_schema(connection: psycopg.Connection) -> None:
    """Create the approved structured-data tables when they do not exist."""
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
