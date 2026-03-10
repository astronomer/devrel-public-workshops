"""
Lightweight MLOps tracking via Airflow connections.
Replaces MLflow's tracking, model registry, and artifact store
with a single SQL database — no external infrastructure needed.

Works with any SQL database reachable through an Airflow connection
(DuckDB, Postgres, MySQL, etc.). Connection ID is configurable via
the MLOPS_TRACKING_CONN_ID environment variable.

Usage in a @task:
    from include.mlops_tracking import MlopsTracker

    tracker = MlopsTracker()
    run_id = tracker.start_run("price_prediction", dag_id="astro_trip_catering_revenue_prediction", task_id="train")
    tracker.log_params(run_id, {"alpha": 0.1, "max_iter": 100})
    tracker.log_metrics(run_id, {"rmse": 42.5, "r2": 0.89})
    tracker.log_model(run_id, "price_model", "LinearRegression", trained_model)
    tracker.log_plot(run_id, "residuals", "scatter", matplotlib_figure)
    tracker.end_run(run_id)
"""

from __future__ import annotations

import base64
import importlib
import io
import json
import logging
import os
import pickle
from typing import Any

log = logging.getLogger(__name__)

TRACKING_CONN_ID = os.environ.get("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")


def _get_hook(conn_id: str):
    from airflow.sdk.bases.hook import BaseHook
    conn = BaseHook.get_connection(conn_id)
    return conn.get_hook()


class MlopsTracker:

    def __init__(self, conn_id: str | None = None):
        self.conn_id = conn_id or TRACKING_CONN_ID
        self._param_marker: str | None = None

    def _hook(self):
        return _get_hook(self.conn_id)

    def _sql(self, template: str) -> str:
        """Adapt qmark-style (?) SQL to the driver's native parameter style.

        DuckDB and SQLite use ``?``, Postgres and MySQL use ``%s``.
        Detection happens once and is cached for the lifetime of the tracker.
        """
        if self._param_marker is None:
            try:
                hook = self._hook()
                conn = hook.get_conn()
                mod = importlib.import_module(type(conn).__module__.split(".")[0])
                style = getattr(mod, "paramstyle", "qmark")
                self._param_marker = "%s" if style in ("format", "pyformat") else "?"
                conn.close()
            except Exception:
                self._param_marker = "?"
        if self._param_marker == "?":
            return template
        return template.replace("?", self._param_marker)

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    def get_or_create_experiment(
        self, experiment_name: str, description: str = ""
    ) -> int:
        hook = self._hook()
        row = hook.get_first(
            self._sql(
                "SELECT experiment_id FROM ml_experiments WHERE experiment_name = ?"
            ),
            parameters=(experiment_name,),
        )
        if row:
            return row[0]

        next_id = hook.get_first(
            "SELECT COALESCE(MAX(experiment_id), 0) + 1 FROM ml_experiments"
        )[0]
        hook.run(
            self._sql(
                "INSERT INTO ml_experiments (experiment_id, experiment_name, description)"
                " VALUES (?, ?, ?)"
            ),
            parameters=(next_id, experiment_name, description),
        )
        return next_id

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def start_run(
        self,
        experiment_name: str,
        dag_id: str,
        task_id: str,
        description: str = "",
        tags: dict | None = None,
    ) -> int:
        experiment_id = self.get_or_create_experiment(experiment_name, description)
        hook = self._hook()
        run_id = hook.get_first(
            "SELECT COALESCE(MAX(run_id), 0) + 1 FROM ml_runs"
        )[0]
        run_number = hook.get_first(
            self._sql(
                "SELECT COALESCE(MAX(run_number), 0) + 1"
                " FROM ml_runs WHERE experiment_id = ?"
            ),
            parameters=(experiment_id,),
        )[0]
        hook.run(
            self._sql(
                "INSERT INTO ml_runs"
                " (run_id, experiment_id, run_number, dag_id, task_id, status, tags)"
                " VALUES (?, ?, ?, ?, ?, 'RUNNING', ?)"
            ),
            parameters=(
                run_id,
                experiment_id,
                run_number,
                dag_id,
                task_id,
                json.dumps(tags or {}),
            ),
        )
        return run_id

    def log_params(self, run_id: int, params: dict[str, Any]) -> None:
        self._hook().run(
            self._sql(
                "UPDATE ml_runs SET hyperparameters = ? WHERE run_id = ?"
            ),
            parameters=(json.dumps(params), run_id),
        )

    def log_metrics(self, run_id: int, metrics: dict[str, float]) -> None:
        self._hook().run(
            self._sql("UPDATE ml_runs SET metrics = ? WHERE run_id = ?"),
            parameters=(json.dumps(metrics), run_id),
        )

    def end_run(self, run_id: int, status: str = "COMPLETED") -> None:
        self._hook().run(
            self._sql("UPDATE ml_runs SET status = ? WHERE run_id = ?"),
            parameters=(status, run_id),
        )

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def log_model(
        self,
        run_id: int,
        model_name: str,
        model_type: str,
        model: Any,
        stage: str = "development",
    ) -> int:
        model_b64 = base64.b64encode(pickle.dumps(model)).decode("utf-8")
        hook = self._hook()
        version = hook.get_first(
            self._sql(
                "SELECT COALESCE(MAX(model_version), 0) + 1"
                " FROM ml_models WHERE model_name = ?"
            ),
            parameters=(model_name,),
        )[0]
        hook.run(
            self._sql(
                "INSERT INTO ml_models"
                " (model_name, model_version, run_id, model_type, model_blob, stage)"
                " VALUES (?, ?, ?, ?, ?, ?)"
            ),
            parameters=(model_name, version, run_id, model_type, model_b64, stage),
        )
        return version

    def load_model(self, model_name: str, stage: str = "production") -> Any:
        row = self._hook().get_first(
            self._sql(
                "SELECT model_blob FROM ml_models"
                " WHERE model_name = ? AND stage = ?"
                " ORDER BY model_version DESC LIMIT 1"
            ),
            parameters=(model_name, stage),
        )
        if not row:
            raise ValueError(f"No model '{model_name}' found in stage '{stage}'")
        return pickle.loads(base64.b64decode(row[0]))

    def promote_model(
        self, model_name: str, model_version: int, stage: str = "production",
        related_names: list[str] | None = None,
    ) -> None:
        """Set one version to *stage* and demote all others.

        When *related_names* is provided, production models for those names
        are also archived (useful for one-production-per-experiment semantics
        across multiple model names).
        """
        hook = self._hook()
        for name in set([model_name] + (related_names or [])):
            hook.run(
                self._sql(
                    "UPDATE ml_models SET stage = 'archived'"
                    " WHERE model_name = ? AND stage = 'production'"
                ),
                parameters=(name,),
            )
        hook.run(
            self._sql(
                "UPDATE ml_models SET stage = ?"
                " WHERE model_name = ? AND model_version = ?"
            ),
            parameters=(stage, model_name, model_version),
        )

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------

    def log_plot(
        self,
        run_id: int,
        plot_name: str,
        plot_type: str,
        fig: Any,
    ) -> int:
        """Serialize a matplotlib figure as base64 PNG and store it."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        hook = self._hook()
        plot_id = hook.get_first(
            "SELECT COALESCE(MAX(plot_id), 0) + 1 FROM ml_plots"
        )[0]
        hook.run(
            self._sql(
                "INSERT INTO ml_plots"
                " (plot_id, run_id, plot_name, plot_type, plot_data)"
                " VALUES (?, ?, ?, ?, ?)"
            ),
            parameters=(plot_id, run_id, plot_name, plot_type, b64),
        )
        return plot_id
