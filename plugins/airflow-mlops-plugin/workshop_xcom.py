"""
Workshop-mode data source: reads ML run data from Airflow XCom.

This module is ONLY used when MLOPS_WORKSHOP_MODE=true. It queries
the Airflow metadata database for XCom entries pushed by the ML DAGs,
and returns them in the same format as the tracking DB queries.
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

_ML_DAG_IDS = ("astro_trip_catering_revenue_prediction", "space_dessert_classification", "food_preference_clustering")
_TRAIN_TASK = "train"
_VIZ_TASK = "visualize"


def _query_xcom(dag_id: str, task_id: str) -> list[dict]:
    """Query XCom for the latest return values from a DAG task.

    Returns a list of deserialized XCom values across all DAG runs,
    ordered by execution_date descending.
    """
    from airflow.models.xcom import XCom
    from airflow.utils.db import provide_session

    @provide_session
    def _fetch(session=None):
        rows = (
            session.query(XCom)
            .filter(
                XCom.dag_id == dag_id,
                XCom.task_id == task_id,
                XCom.key == "return_value",
            )
            .order_by(XCom.timestamp.desc())
            .limit(20)
            .all()
        )
        results = []
        for row in rows:
            try:
                val = row.value
                if isinstance(val, str):
                    val = json.loads(val)
                if isinstance(val, dict):
                    results.append(val)
            except Exception:
                continue
        return results

    try:
        return _fetch()
    except Exception as e:
        log.warning("Failed to query XCom for %s/%s: %s", dag_id, task_id, e)
        return []


def get_xcom_experiments() -> list[dict]:
    """Build experiment list from XCom train task outputs."""
    seen = {}
    for dag_id in _ML_DAG_IDS:
        runs = _query_xcom(dag_id, _TRAIN_TASK)
        for run_data in runs:
            exp_name = run_data.get("experiment", dag_id)
            if exp_name not in seen:
                seen[exp_name] = {
                    "experiment_id": hash(exp_name) % 100000,
                    "experiment_name": exp_name,
                    "description": f"From DAG {dag_id}",
                }
    return list(seen.values())


def get_xcom_runs(experiment_name: str | None = None) -> list[dict]:
    """Build run list from XCom train task outputs."""
    runs = []
    for dag_id in _ML_DAG_IDS:
        xcom_runs = _query_xcom(dag_id, _TRAIN_TASK)
        for run_data in xcom_runs:
            exp = run_data.get("experiment", dag_id)
            if experiment_name and exp != experiment_name:
                continue
            runs.append({
                "run_id": run_data.get("run_id", 0),
                "run_number": run_data.get("run_id", 0),
                "experiment_name": exp,
                "dag_id": run_data.get("dag_id", dag_id),
                "task_id": _TRAIN_TASK,
                "status": "COMPLETED",
                "metrics": run_data.get("metrics", {}),
                "params": run_data.get("params", {}),
                "model_name": run_data.get("model_name"),
                "model_type": run_data.get("model_type"),
                "model_version": run_data.get("model_version"),
                "source": "xcom",
            })
    return runs


def get_xcom_models() -> list[dict]:
    """Build model registry from XCom train task outputs."""
    models = []
    for dag_id in _ML_DAG_IDS:
        xcom_runs = _query_xcom(dag_id, _TRAIN_TASK)
        for run_data in xcom_runs:
            if "model_name" not in run_data:
                continue
            models.append({
                "model_version": run_data.get("model_version", 0),
                "run_id": run_data.get("run_id", 0),
                "model_name": run_data["model_name"],
                "model_type": run_data.get("model_type", "unknown"),
                "stage": "development",
                "has_artifact": bool(run_data.get("model_b64")),
                "source": "xcom",
            })
    return models


def get_xcom_plots(run_id: int | None = None) -> list[dict]:
    """Build plot list from XCom visualize task outputs."""
    plots = []
    for dag_id in _ML_DAG_IDS:
        xcom_viz = _query_xcom(dag_id, _VIZ_TASK)
        for viz_data in xcom_viz:
            if run_id is not None and viz_data.get("run_id") != run_id:
                continue
            for p in viz_data.get("plots", []):
                plots.append({
                    "run_id": viz_data.get("run_id", 0),
                    "plot_name": p.get("name", "plot"),
                    "plot_type": p.get("type", "image"),
                    "plot_data": p.get("data_b64", ""),
                    "source": "xcom",
                })
    return plots


def get_xcom_model_artifact(dag_id: str, model_name: str) -> str | None:
    """Retrieve the base64-encoded model artifact from XCom."""
    xcom_runs = _query_xcom(dag_id, _TRAIN_TASK)
    for run_data in xcom_runs:
        if run_data.get("model_name") == model_name and run_data.get("model_b64"):
            return run_data["model_b64"]
    return None
