"""
MLOps Plugin for Apache Airflow 3.1+

Provides an experiment tracker, model registry, and visualization gallery
directly inside the Airflow UI — no MLflow server needed.

Data sources:
  - Primary: reads from the Airflow Variable ``mlops_plugin_data``, which
    is populated by the ``plugin_sync`` DAG running on a worker.
  - Fallback: reads directly from the DuckDB file at
    $AIRFLOW_HOME/include/astrotrips.duckdb (works locally where the
    API server and workers share a filesystem).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from airflow.plugins_manager import AirflowPlugin

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = os.path.join(
    os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"),
    "include",
    "astrotrips.duckdb",
)

# Inline the nav icon as a data URI. A path here is resolved against the UI's
# <base href>, so an absolute /mlops/... path drops Astro's deployment sub-path
# and 404s in the cloud. A data URI renders with no fetch, base path or proxy.
_ICON_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(
    (BASE_DIR / "assets" / "icon.svg").read_bytes()
).decode("ascii")

app = FastAPI(title="MLOps Plugin")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")


# ---------------------------------------------------------------------------
# Variable-based data source (set by plugin_sync DAG)
# ---------------------------------------------------------------------------

def _load_from_variable() -> dict | None:
    """Load ML tracking data from the Airflow Variable set by plugin_sync.

    Returns dict with experiments/runs/models/plots keys, or None.
    """
    try:
        from airflow.models import Variable
        return json.loads(Variable.get("mlops_plugin_data"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# DuckDB fallback (works locally where API server shares the worker filesystem)
# ---------------------------------------------------------------------------

def _db_records(sql: str, params: tuple = ()) -> list[tuple]:
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows
    except Exception as e:
        log.warning("DB query failed: %s", e)
        return []


def _db_first(sql: str, params: tuple = ()) -> tuple | None:
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows[0] if rows else None
    except Exception as e:
        log.warning("DB query failed: %s", e)
        return None


def _db_run(sql: str, params: tuple = ()) -> None:
    try:
        conn = duckdb.connect(DB_PATH)
        conn.execute(sql, params)
        conn.close()
    except Exception as e:
        log.warning("DB write failed: %s", e)


def _safe_json(val) -> dict:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


# ---------------------------------------------------------------------------
# UI entry point
# ---------------------------------------------------------------------------

@app.get("/ui", response_class=FileResponse)
async def serve_ui():
    return FileResponse(BASE_DIR / "static" / "index.html")


# ---------------------------------------------------------------------------
# API: Summary
# ---------------------------------------------------------------------------

@app.get("/api/summary")
async def get_summary():
    def _fetch():
        var_data = _load_from_variable()
        if var_data:
            return {
                "experiments": len(var_data.get("experiments", [])),
                "runs": len(var_data.get("runs", [])),
                "models": len(var_data.get("models", [])),
                "plots": len(var_data.get("plots", [])),
            }

        exp_count = (_db_first("SELECT count(*) FROM ml_experiments") or (0,))[0]
        run_count = (_db_first("SELECT count(*) FROM ml_runs") or (0,))[0]
        model_count = (_db_first("SELECT count(*) FROM ml_models") or (0,))[0]
        plot_count = (_db_first("SELECT count(*) FROM ml_plots") or (0,))[0]
        return {
            "experiments": exp_count,
            "runs": run_count,
            "models": model_count,
            "plots": plot_count,
        }

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Experiments
# ---------------------------------------------------------------------------

@app.get("/api/experiments")
async def list_experiments():
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "experiments" in var_data:
            return [
                {"experiment_id": r[0], "experiment_name": r[1],
                 "description": r[2], "source": "variable"}
                for r in var_data["experiments"]
            ]

        rows = _db_records(
            "SELECT experiment_id, experiment_name, description"
            " FROM ml_experiments ORDER BY experiment_id"
        )
        return [
            {"experiment_id": r[0], "experiment_name": r[1],
             "description": r[2], "source": "db"}
            for r in rows
        ]

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Runs
# ---------------------------------------------------------------------------

@app.get("/api/runs")
async def list_runs(experiment: str | None = Query(default=None)):
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "runs" in var_data:
            return [
                {
                    "run_id": r[0], "experiment_name": r[1], "dag_id": r[2],
                    "task_id": r[3], "status": r[4],
                    "params": _safe_json(r[5]), "metrics": _safe_json(r[6]),
                    "tags": _safe_json(r[7]),
                    "run_ts": str(r[8]) if r[8] else None,
                    "run_number": r[9],
                    "source": "variable",
                }
                for r in var_data["runs"]
                if not experiment or r[1] == experiment
            ]

        cols = ("SELECT r.run_id, e.experiment_name, r.dag_id, r.task_id,"
                " r.status, r.hyperparameters, r.metrics, r.tags, r.run_ts,"
                " r.run_number")
        if experiment:
            rows = _db_records(
                cols + " FROM ml_runs r"
                " JOIN ml_experiments e ON r.experiment_id = e.experiment_id"
                " WHERE e.experiment_name = ?"
                " ORDER BY r.run_ts, r.run_id",
                (experiment,),
            )
        else:
            rows = _db_records(
                cols + " FROM ml_runs r"
                " JOIN ml_experiments e ON r.experiment_id = e.experiment_id"
                " ORDER BY r.run_ts DESC, r.run_id DESC"
            )
        return [
            {
                "run_id": r[0], "experiment_name": r[1], "dag_id": r[2],
                "task_id": r[3], "status": r[4],
                "params": _safe_json(r[5]), "metrics": _safe_json(r[6]),
                "tags": _safe_json(r[7]),
                "run_ts": str(r[8]) if r[8] else None,
                "run_number": r[9],
                "source": "db",
            }
            for r in rows
        ]

    return await asyncio.to_thread(_fetch)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "runs" in var_data:
            for r in var_data["runs"]:
                if r[0] == run_id:
                    return {
                        "run_id": r[0], "experiment_name": r[1], "dag_id": r[2],
                        "task_id": r[3], "status": r[4],
                        "params": _safe_json(r[5]), "metrics": _safe_json(r[6]),
                        "tags": _safe_json(r[7]), "run_number": r[9],
                        "source": "variable",
                    }
            return None

        row = _db_first(
            "SELECT r.run_id, e.experiment_name, r.dag_id, r.task_id,"
            " r.status, r.hyperparameters, r.metrics, r.tags, r.run_number"
            " FROM ml_runs r"
            " JOIN ml_experiments e ON r.experiment_id = e.experiment_id"
            " WHERE r.run_id = ?",
            (run_id,),
        )
        if row:
            return {
                "run_id": row[0], "experiment_name": row[1], "dag_id": row[2],
                "task_id": row[3], "status": row[4],
                "params": _safe_json(row[5]), "metrics": _safe_json(row[6]),
                "tags": _safe_json(row[7]), "run_number": row[8],
                "source": "db",
            }
        return None

    result = await asyncio.to_thread(_fetch)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


# ---------------------------------------------------------------------------
# API: Plots
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/plots")
async def get_plots(run_id: int):
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "plots" in var_data:
            return [
                {"plot_id": r[0], "run_id": r[1], "plot_name": r[2],
                 "plot_type": r[3], "plot_data": r[4], "source": "variable"}
                for r in var_data["plots"]
                if r[1] == run_id
            ]

        rows = _db_records(
            "SELECT plot_id, plot_name, plot_type, plot_data"
            " FROM ml_plots WHERE run_id = ?",
            (run_id,),
        )
        return [
            {"plot_id": r[0], "plot_name": r[1], "plot_type": r[2],
             "plot_data": r[3], "source": "db"}
            for r in rows
        ]

    return await asyncio.to_thread(_fetch)


@app.get("/api/plots")
async def list_all_plots():
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "plots" in var_data:
            return [
                {"plot_id": r[0], "run_id": r[1], "plot_name": r[2],
                 "plot_type": r[3], "plot_data": r[4],
                 "experiment_name": r[5], "source": "variable"}
                for r in var_data["plots"]
            ]

        rows = _db_records(
            "SELECT p.plot_id, p.run_id, p.plot_name, p.plot_type, p.plot_data,"
            " e.experiment_name"
            " FROM ml_plots p"
            " JOIN ml_runs r ON p.run_id = r.run_id"
            " JOIN ml_experiments e ON r.experiment_id = e.experiment_id"
            " ORDER BY p.plot_id DESC"
        )
        return [
            {"plot_id": r[0], "run_id": r[1], "plot_name": r[2],
             "plot_type": r[3], "plot_data": r[4],
             "experiment_name": r[5], "source": "db"}
            for r in rows
        ]

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Model registry
# ---------------------------------------------------------------------------

@app.get("/api/models")
async def list_models():
    def _fetch():
        var_data = _load_from_variable()
        if var_data and "models" in var_data:
            return [
                {"model_name": r[0], "model_version": r[1], "run_id": r[2],
                 "model_type": r[3], "stage": r[4], "source": "variable"}
                for r in var_data["models"]
            ]

        rows = _db_records(
            "SELECT model_name, model_version, run_id, model_type, stage"
            " FROM ml_models ORDER BY model_name, model_version DESC"
        )
        return [
            {"model_name": r[0], "model_version": r[1], "run_id": r[2],
             "model_type": r[3], "stage": r[4], "source": "db"}
            for r in rows
        ]

    return await asyncio.to_thread(_fetch)


@app.patch("/api/models/{model_name}/{model_version}/stage")
async def update_model_stage(model_name: str, model_version: int, stage: str = Query(...)):
    def _update():
        _db_run(
            "UPDATE ml_models SET stage = ? WHERE model_name = ? AND model_version = ?",
            (stage, model_name, model_version),
        )
        return {"model_name": model_name, "model_version": model_version, "stage": stage}

    return await asyncio.to_thread(_update)


@app.get("/api/models/{model_name}/{model_version}/artifact")
async def get_model_artifact(model_name: str, model_version: int):
    def _fetch():
        row = _db_first(
            "SELECT model_blob FROM ml_models WHERE model_name = ? AND model_version = ?",
            (model_name, model_version),
        )
        if row:
            return {"model_b64": row[0], "model_name": model_name, "source": "db"}
        return None

    result = await asyncio.to_thread(_fetch)
    if not result:
        raise HTTPException(status_code=404, detail="Model artifact not found")
    return result


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

class MlopsPlugin(AirflowPlugin):
    name = "mlops_plugin"

    fastapi_apps = [
        {
            "app": app,
            "url_prefix": "/mlops",
            "name": "MLOps Plugin",
        }
    ]

    external_views = [
        {
            "name": "MLOps Plugin",
            "href": "mlops/ui",
            "destination": "nav",
            "category": "browse",
            "url_route": "mlops",
            "icon": _ICON_DATA_URI,
        }
    ]
