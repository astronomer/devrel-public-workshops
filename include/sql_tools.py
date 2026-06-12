"""Read-only SQL tools over the AstroTrips DuckDB for the email agents.

The common-ai SQLToolset expects a modern common-sql DbApiHook (get_table_schema,
inspector, last_description), which the pinned airflow-provider-duckdb hook does
not implement. These tools expose the same capability over the DuckDB connection
rag.py already uses: read-only, scoped to the AstroTrips business tables. A bad
table or query raises ModelRetry so the agent corrects itself instead of failing.
"""

from __future__ import annotations

import json
import logging

from pydantic_ai import FunctionToolset, ModelRetry

log = logging.getLogger(__name__)

_ALLOWED_TABLES = frozenset({
    "menu_items", "meal_orders", "cosmarket_orders",
})
_MAX_ROWS = 50


def _connect():
    from include.aimlops.persistence import get_duckdb_conn

    return get_duckdb_conn(read_only=True)


def list_tables() -> str:
    """List the AstroTrips tables you can query.

    Call this first, before get_schema or query, to see what data is available.
    """
    conn = _connect()
    try:
        present = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
    finally:
        conn.close()
    result = json.dumps(sorted(t for t in _ALLOWED_TABLES if t in present))
    log.info("list_tables -> %s", result)
    return result


def get_schema(table_name: str) -> str:
    """Return a table's columns as a list of {column, type}.

    Call this before query so you use the table's real column names instead of
    guessing them.
    """
    if table_name not in _ALLOWED_TABLES:
        raise ModelRetry(
            f"{table_name!r} is not an available table. Call list_tables to see "
            "what you can query."
        )
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table_name],
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        raise ModelRetry(f"{table_name!r} has no columns or does not exist.")
    result = json.dumps([{"column": r[0], "type": r[1]} for r in rows])
    log.info("get_schema(%r) -> %s", table_name, result)
    return result


def query(sql: str) -> str:
    """Run one read-only SQL SELECT against the AstroTrips database.

    Returns up to 50 rows as JSON. Only SELECT is allowed. Learn a table's
    columns with get_schema first; do not guess column or table names.
    """
    log.info("query: %s", " ".join(sql.split()))
    conn = _connect()
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(_MAX_ROWS)
    except Exception as e:
        log.info("query failed: %s", e)
        raise ModelRetry(
            f"Query failed: {e}. Use list_tables and get_schema to check the exact "
            "table and column names, then try again."
        ) from e
    finally:
        conn.close()
    result = json.dumps([dict(zip(columns, row)) for row in rows], default=str)
    log.info("query -> %d rows: %s", len(rows), result)
    return result


SQL_TOOLSET = FunctionToolset(tools=[list_tables, get_schema, query])
