from pathlib import Path
import os

from airflow.configuration import AIRFLOW_HOME
from airflow.sdk import Asset, dag, task

_DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_SEED_DIR = Path(AIRFLOW_HOME) / "include" / "seed"


@dag(tags=["exercise 1"])
def load_trained_model_examples():

    @task(outlets=[Asset("plugin_sync")])
    def seed_ml_tracking():
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

    seed_ml_tracking()


load_trained_model_examples()
