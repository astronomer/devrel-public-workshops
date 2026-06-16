"""Spend-estimate tool: runs the spend_inference DAG as a tool for the drafter agent.

estimate_spend triggers spend_inference via the Airflow REST API with the prospect
as run conf, waits for the run to finish, and reads the food-spend-per-day-per-person
estimate the DAG wrote to DuckDB (spend_predictions). Exposed as PREDICT_FOOD_SPEND_TOOL.
"""

from __future__ import annotations

import logging

from pydantic_ai import FunctionToolset

log = logging.getLogger(__name__)

_DAG_ID = "spend_inference"


def estimate_spend(prospect: dict) -> dict:
    """Estimate this prospect's food spend per person per day with the current best model.

    Runs the spend_inference pipeline (feature engineering plus the best registered
    model) for the prospect and returns its prediction. Call this when you need a
    data-driven spend estimate to size an offer for the prospect.

    Args:
        prospect: Structured details of the prospect and their proposed trip, for
            example customer_id, destination, passengers, trip_length_days, and rough
            timing, for the model to score.

    Returns:
        A dict with food_spend_pp_pd (USD per person per day, or None if the run
        produced no estimate) and the dag_run_id that produced it.
    """
    from include.aimlops.persistence import get_duckdb_conn
    from include.airflow_api import trigger_dag_run, wait_for_dag_run

    dag_run_id = trigger_dag_run(_DAG_ID, {"prospect": prospect})
    state = wait_for_dag_run(_DAG_ID, dag_run_id)
    if state != "success":
        log.warning("spend_inference run %s ended in state=%s", dag_run_id, state)
        return {"dag_run_id": dag_run_id, "food_spend_pp_pd": None}

    conn = get_duckdb_conn()
    try:
        row = conn.execute(
            "SELECT food_spend_pp_pd FROM spend_predictions WHERE dag_run_id = ?",
            [dag_run_id],
        ).fetchone()
    finally:
        conn.close()

    estimate = row[0] if row else None
    log.info("estimate_spend dag_run_id=%s -> food_spend_pp_pd=%s", dag_run_id, estimate)
    try:
        from airflow.sdk import get_current_context

        get_current_context()["ti"].xcom_push(key="estimated_spend", value=estimate)
    except Exception as e:
        log.warning("could not lock in estimated_spend via XCom: %s", e)
    return {"dag_run_id": dag_run_id, "food_spend_pp_pd": estimate}


PREDICT_FOOD_SPEND_TOOL = FunctionToolset(tools=[estimate_spend])
