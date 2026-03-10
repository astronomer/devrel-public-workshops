import os
from pathlib import Path

from airflow.configuration import AIRFLOW_HOME
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sdk import Asset, dag, chain, task

_DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_SEED_DIR = Path(AIRFLOW_HOME) / "include" / "seed"


@dag(tags=["setup"], template_searchpath=f"{AIRFLOW_HOME}/include/sql")
def setup():

    @task
    def cleanup():
        """Remove existing database file to start fresh."""
        db_dir = Path(AIRFLOW_HOME) / "include"
        for p in db_dir.glob("astrotrips.duckdb*"):
            p.chmod(0o644)
            p.unlink()

    _cleanup = cleanup()

    _schema = SQLExecuteQueryOperator(
        task_id="schema", conn_id=_DUCKDB_CONN_ID, sql="schema.sql"
    )

    _ml_schema = SQLExecuteQueryOperator(
        task_id="ml_schema", conn_id=_DUCKDB_CONN_ID, sql="ml_schema.sql"
    )

    _fixtures = SQLExecuteQueryOperator(
        task_id="fixtures", conn_id=_DUCKDB_CONN_ID, sql="fixtures.sql"
    )

    _ml_data = SQLExecuteQueryOperator(
        task_id="ml_data", conn_id=_DUCKDB_CONN_ID, sql="generate_ml_data.sql"
    )

    _food_data = SQLExecuteQueryOperator(
        task_id="food_data", conn_id=_DUCKDB_CONN_ID, sql="generate_food_data.sql"
    )

    @task(outlets=[Asset("plugin_sync"), Asset("db_reload")])
    def seed_ml_tracking():
        """Load pre-generated ML tracking data from CSV files into DuckDB."""
        from airflow.sdk.bases.hook import BaseHook

        tables = ["ml_experiments", "ml_runs", "ml_models", "ml_plots"]
        hook = BaseHook.get_connection(_DUCKDB_CONN_ID).get_hook()
        conn = hook.get_conn()

        for table in tables:
            csv_path = _SEED_DIR / f"{table}.csv"
            if not csv_path.exists():
                continue
            conn.execute(f"DELETE FROM {table}")
            conn.execute(
                f"INSERT INTO {table} SELECT * "
                f"FROM read_csv_auto('{csv_path}', max_line_size=50000000)"
            )

        conn.close()

    chain(
        _cleanup,
        _schema,
        _ml_schema,
        _fixtures,
        _ml_data,
        _food_data,
        seed_ml_tracking(),
    )


setup_dag = setup()

if __name__ == "__main__":
    setup_dag.test(conn_file_path="include/connections.yaml")
