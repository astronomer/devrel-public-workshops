"""
MLOps Plugin for Apache Airflow 3.1+

Provides an experiment tracker, model registry, and visualization gallery
directly inside the Airflow UI — no MLflow server needed.

Data sources:
  - Production mode (default): reads directly from the DuckDB file at
    $AIRFLOW_HOME/include/astrotrips.duckdb (no Airflow connection needed).
  - Workshop mode (MLOPS_WORKSHOP_MODE=true): also reads live participant
    data from XCom entries pushed by the ML DAGs.
"""

from __future__ import annotations

import asyncio
import importlib.util
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
WORKSHOP_MODE = os.environ.get("MLOPS_WORKSHOP_MODE", "").lower() in ("true", "1", "yes")
DB_PATH = os.path.join(
    os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"),
    "include",
    "astrotrips.duckdb",
)

app = FastAPI(title="MLOps Plugin")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")


# ---------------------------------------------------------------------------
# Workshop XCom module — lazy-loaded from same directory, gracefully absent
# ---------------------------------------------------------------------------

_workshop_mod = None


def _ws():
    """Load workshop_xcom.py if workshop mode is active and file exists."""
    global _workshop_mod
    if _workshop_mod is not None:
        return _workshop_mod
    xcom_path = BASE_DIR / "workshop_xcom.py"
    if not xcom_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("workshop_xcom", xcom_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _workshop_mod = mod
    return mod



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
        exp_count = (_db_first("SELECT count(*) FROM ml_experiments") or (0,))[0]
        run_count = (_db_first("SELECT count(*) FROM ml_runs") or (0,))[0]
        model_count = (_db_first("SELECT count(*) FROM ml_models") or (0,))[0]
        plot_count = (_db_first("SELECT count(*) FROM ml_plots") or (0,))[0]

        if WORKSHOP_MODE and _ws():
            exp_count += len(_ws().get_xcom_experiments())
            run_count += len(_ws().get_xcom_runs())
            model_count += len(_ws().get_xcom_models())
            plot_count += len(_ws().get_xcom_plots())

        return {
            "experiments": exp_count,
            "runs": run_count,
            "models": model_count,
            "plots": plot_count,
            "workshop_mode": WORKSHOP_MODE,
        }

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Experiments
# ---------------------------------------------------------------------------

@app.get("/api/experiments")
async def list_experiments():
    def _fetch():
        rows = _db_records(
            "SELECT experiment_id, experiment_name, description"
            " FROM ml_experiments ORDER BY experiment_id"
        )
        experiments = [
            {"experiment_id": r[0], "experiment_name": r[1],
             "description": r[2], "source": "db"}
            for r in rows
        ]
        if WORKSHOP_MODE and _ws():
            seen = {e["experiment_name"] for e in experiments}
            experiments.extend(
                e for e in _ws().get_xcom_experiments()
                if e["experiment_name"] not in seen
            )
        return experiments

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Runs
# ---------------------------------------------------------------------------

@app.get("/api/runs")
async def list_runs(experiment: str | None = Query(default=None)):
    def _fetch():
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

        runs = [
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

        if WORKSHOP_MODE and _ws():
            seen_ids = {r["run_id"] for r in runs}
            runs.extend(
                r for r in _ws().get_xcom_runs(experiment)
                if r["run_id"] not in seen_ids
            )
        return runs

    return await asyncio.to_thread(_fetch)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    def _fetch():
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
        if WORKSHOP_MODE and _ws():
            for r in _ws().get_xcom_runs():
                if r["run_id"] == run_id:
                    return r
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
        rows = _db_records(
            "SELECT plot_id, plot_name, plot_type, plot_data"
            " FROM ml_plots WHERE run_id = ?",
            (run_id,),
        )
        plots = [
            {"plot_id": r[0], "plot_name": r[1], "plot_type": r[2],
             "plot_data": r[3], "source": "db"}
            for r in rows
        ]
        if WORKSHOP_MODE and _ws():
            plots.extend(_ws().get_xcom_plots(run_id))
        return plots

    return await asyncio.to_thread(_fetch)


@app.get("/api/plots")
async def list_all_plots():
    def _fetch():
        rows = _db_records(
            "SELECT p.plot_id, p.run_id, p.plot_name, p.plot_type, p.plot_data,"
            " e.experiment_name"
            " FROM ml_plots p"
            " JOIN ml_runs r ON p.run_id = r.run_id"
            " JOIN ml_experiments e ON r.experiment_id = e.experiment_id"
            " ORDER BY p.plot_id DESC"
        )
        plots = [
            {"plot_id": r[0], "run_id": r[1], "plot_name": r[2],
             "plot_type": r[3], "plot_data": r[4],
             "experiment_name": r[5], "source": "db"}
            for r in rows
        ]
        if WORKSHOP_MODE and _ws():
            plots.extend(_ws().get_xcom_plots())
        return plots

    return await asyncio.to_thread(_fetch)


# ---------------------------------------------------------------------------
# API: Model registry
# ---------------------------------------------------------------------------

@app.get("/api/models")
async def list_models():
    def _fetch():
        rows = _db_records(
            "SELECT model_name, model_version, run_id, model_type, stage"
            " FROM ml_models ORDER BY model_name, model_version DESC"
        )
        models = [
            {"model_name": r[0], "model_version": r[1], "run_id": r[2],
             "model_type": r[3], "stage": r[4], "source": "db"}
            for r in rows
        ]
        if WORKSHOP_MODE and _ws():
            seen = {(m["model_name"], m["model_version"]) for m in models}
            models.extend(
                m for m in _ws().get_xcom_models()
                if (m["model_name"], m["model_version"]) not in seen
            )
        return models

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
        }
    ]
