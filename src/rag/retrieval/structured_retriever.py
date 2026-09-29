"""Generate, validate, and execute SQL for structured retrieval."""

import logging

import ollama
import sqlglot
from psycopg.rows import dict_row
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope

from config.settings import (
    DATABASE_SCHEMA,
    LOCAL_MODEL_NAME,
    SQL_GENERATION_PROMPT,
    SQL_GENERATION_SYSTEM_PROMPT,
)
from src.etl.db.db import connect_database

logger = logging.getLogger(__name__)

APPROVED_TABLES = frozenset({"competition", "events", "lineups", "matches"})
APPROVED_SCHEMAS = frozenset({"public"})
COMMENT_MARKERS = ("--", "/*", "*/")
BLOCKED_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Create,
    exp.Grant,
    exp.Revoke,
    exp.Into,
)


def generate_sql(query: str) -> str:
    """Generate a SQL query for a natural-language question.

    Args:
        query: The user's natural-language question.

    Returns:
        A SQL query that can be checked by ``validate_sql``.
    """
    logger.info("Generating structured SQL for question: %r", query)
    system_prompt = SQL_GENERATION_SYSTEM_PROMPT.format(
        database_schema=DATABASE_SCHEMA,
    )
    prompt = SQL_GENERATION_PROMPT.format(user_query=query)

    try:
        response = ollama.generate(
            model=LOCAL_MODEL_NAME,
            prompt=prompt,
            system=system_prompt,
            options={
                "temperature": 0.0  # Eliminates randomness for exact coding tasks
            },
        )
    except Exception:
        logger.exception("Structured SQL generation failed.")
        raise

    sql_query = response["response"].strip()
    logger.info("Generated structured SQL: %s", sql_query)
    return sql_query


def validate_sql(sql_query: str) -> bool:
    """Return whether a generated SQL query is safe for read-only execution.

    Args:
        sql_query: SQL produced by ``generate_sql``.

    Returns:
        ``True`` when the query passes every validation rule; otherwise ``False``.
    """
    if not isinstance(sql_query, str) or not sql_query.strip():
        logger.warning("SQL validation rejected an empty or non-text query.")
        return False

    logger.info("Validating structured SQL: %s", sql_query)
    if any(marker in sql_query for marker in COMMENT_MARKERS):
        logger.warning("SQL validation rejected a query containing comments.")
        return False

    try:
        statements = sqlglot.parse(sql_query, read="postgres")
    except SqlglotError as error:
        logger.warning("SQL validation could not parse the query: %s", error)
        return False

    if len(statements) != 1 or statements[0] is None:
        logger.warning(
            "SQL validation requires exactly one statement; parsed %d.",
            len(statements),
        )
        return False

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        logger.warning(
            "SQL validation rejected non-SELECT statement type %s.",
            type(statement).__name__,
        )
        return False

    for node_type in BLOCKED_EXPRESSIONS:
        if statement.find(node_type) is not None:
            logger.warning(
                "SQL validation rejected blocked expression %s.",
                node_type.__name__,
            )
            return False

    for scope in traverse_scope(statement):
        for source in scope.sources.values():
            if not isinstance(source, exp.Table):
                continue

            table_name = source.name.lower()
            schema_name = source.db.lower()
            catalog_name = source.catalog.lower()

            if table_name not in APPROVED_TABLES:
                logger.warning(
                    "SQL validation rejected unapproved table %r.",
                    table_name,
                )
                return False
            if schema_name and schema_name not in APPROVED_SCHEMAS:
                logger.warning(
                    "SQL validation rejected unapproved schema %r.",
                    schema_name,
                )
                return False
            if catalog_name:
                logger.warning(
                    "SQL validation rejected catalog-qualified table %r.",
                    source.sql(dialect="postgres"),
                )
                return False

    logger.info("Structured SQL passed read-only validation.")
    return True


def execute_sql(sql_query: str) -> list[dict[str, object]]:
    """Execute validated read-only SQL and return named result rows.

    Args:
        sql_query: A SQL query that has passed ``validate_sql``.

    Returns:
        Result rows represented as dictionaries keyed by column name.
    """
    if not validate_sql(sql_query):
        logger.error("Structured SQL execution stopped because validation failed.")
        raise ValueError("SQL query failed read-only validation.")

    logger.info("Executing validated structured SQL: %s", sql_query)
    try:
        with connect_database() as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout = '5s'")

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql_query)
                rows = list(cursor.fetchall())
    except Exception:
        logger.exception("Structured SQL execution failed for query: %s", sql_query)
        raise

    if rows:
        logger.info("Structured SQL returned %d row(s).", len(rows))
        logger.debug("Structured SQL result rows: %r", rows)
    else:
        logger.warning("Structured SQL returned 0 rows for query: %s", sql_query)

    return rows
