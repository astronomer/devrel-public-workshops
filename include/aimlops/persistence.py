import json
import os

import duckdb
from airflow.sdk import BaseHook, Variable

DEMO_SYNC_ENV = "AIMLOPS_DEMO_SYNC"
DB_PATH_ENV = "AIMLOPS_DB_PATH"
DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
VARIABLE_PREFIX = "aimlops_"


def is_demo_env() -> bool:
    return os.getenv(DEMO_SYNC_ENV, "0") == "1"


def get_duckdb_conn(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = os.getenv(DB_PATH_ENV) or BaseHook.get_connection(DUCKDB_CONN_ID).host
    return duckdb.connect(path, read_only=read_only)


def replace_table(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    columns: list[str],
    records: list[dict],
) -> None:
    # Overwrite a table's contents: clear it, then bulk-insert the given records.
    conn.execute(f"DELETE FROM {table}")
    if not records:
        return
    collist = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    rows = [[r[c] for c in columns] for r in records]
    conn.executemany(
        f"INSERT INTO {table} ({collist}) VALUES ({placeholders})", rows
    )


def _records(table: str) -> list[dict]:
    with get_duckdb_conn() as conn:
        result = conn.execute(f"SELECT * FROM {table}")
        columns = [col[0] for col in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]


def sync_table_to_variable(table: str) -> None:
    # In the Astro IDE demo env the worker filesystem isn't shared, so mirror the
    # table into an Airflow Variable every worker can read. No-op when running locally.
    if is_demo_env():
        Variable.set(f"{VARIABLE_PREFIX}{table}", json.dumps(_records(table), default=str))


def load_records(table: str) -> list[dict]:
    # Read a table from DuckDB locally, or from its synced Variable in the demo env.
    if is_demo_env():
        return json.loads(Variable.get(f"{VARIABLE_PREFIX}{table}", default_var="[]"))
    return _records(table)
