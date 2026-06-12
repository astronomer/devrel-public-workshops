"""
DO NOT MODIFY!

Syncs DuckDB ML tracking data to an Airflow Variable.

Workaround for Astro deployments where the MLOps plugin runs on the
API server, which does not share the worker's filesystem.  This DAG reads
all ML tracking data from DuckDB (on the worker) and writes it as JSON
to an Airflow Variable that the plugin can read from anywhere.

Locally this DAG is optional — the plugin falls back to reading DuckDB directly.

This workaround can also be avoided entirely by using a cloud-hosted DuckDB
via MotherDuck (https://motherduck.com). Both the worker and the API server
can then connect to the same remote database.

Please do not change this code during the workshop!
"""

import json
import os

from airflow.models import Variable
from airflow.sdk import Asset, dag, task, Asset

_DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")


def _serialize(obj):
    from datetime import datetime

    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


@dag(
    schedule=[Asset("plugin_sync")],
    tags=["mlops", "plugin"],
    doc_md=__doc__,
    is_paused_upon_creation=False
)
def plugin_sync():

    @task
    def sync_to_variable():
        import duckdb
        from airflow.sdk.bases.hook import BaseHook

        db_path = BaseHook.get_connection(_DUCKDB_CONN_ID).host
        conn = duckdb.connect(db_path, read_only=True)

        experiments = conn.execute(
            "SELECT experiment_id, experiment_name, description "
            "FROM ml_experiments ORDER BY experiment_id"
        ).fetchall()

        runs = conn.execute(
            "SELECT r.run_id, e.experiment_name, r.dag_id, r.task_id, "
            "r.status, r.hyperparameters, r.metrics, r.tags, r.run_ts, "
            "r.run_number "
            "FROM ml_runs r "
            "JOIN ml_experiments e ON r.experiment_id = e.experiment_id "
            "ORDER BY r.run_ts DESC, r.run_id DESC"
        ).fetchall()

        models = conn.execute(
            "SELECT model_name, model_version, run_id, model_type, stage "
            "FROM ml_models ORDER BY model_name, model_version DESC"
        ).fetchall()

        plots = conn.execute(
            "SELECT p.plot_id, p.run_id, p.plot_name, p.plot_type, p.plot_data, "
            "e.experiment_name "
            "FROM ml_plots p "
            "JOIN ml_runs r ON p.run_id = r.run_id "
            "JOIN ml_experiments e ON r.experiment_id = e.experiment_id "
            "ORDER BY p.plot_id DESC"
        ).fetchall()

        conn.close()

        Variable.set(
            "mlops_plugin_data",
            json.dumps(
                {
                    "experiments": experiments,
                    "runs": runs,
                    "models": models,
                    "plots": plots,
                },
                default=_serialize,
            ),
        )

    sync_to_variable()


plugin_sync()
