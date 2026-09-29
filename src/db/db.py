"""Database connection entry points."""

from urllib.parse import unquote, urlsplit, urlunsplit

import psycopg
from psycopg import sql

from config.settings import DATABASE_URL


def create_database_if_missing() -> None:
    """Create the configured PostgreSQL database when it does not exist."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy .env.example to .env and "
            "provide local PostgreSQL credentials."
        )

    parsed_url = urlsplit(DATABASE_URL)
    database_name = unquote(parsed_url.path.lstrip("/"))
    if not database_name:
        raise ValueError("DATABASE_URL must include a database name.")

    maintenance_url = urlunsplit(parsed_url._replace(path="/postgres"))
    with psycopg.connect(maintenance_url, autocommit=True) as connection:
        database_exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,),
        ).fetchone()
        if database_exists is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )


def connect_database() -> psycopg.Connection:
    """Ensure the configured database exists, then open and return a connection.

    The caller is responsible for closing the returned connection, preferably
    by using it as a context manager.
    """
    create_database_if_missing()
    return psycopg.connect(DATABASE_URL)
