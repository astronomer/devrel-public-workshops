"""Trigger Airflow DAGs via the REST API and wait for completion.

Used by agent tools that run a DAG as a tool. This does NOT use Airflow
connections. Auth switches on the ENVIRONMENT env var:
- local: exchange username/password for a short-lived JWT at /auth/token.
- astro: use a deployment bearer token from AIRFLOW_API_TOKEN (workshop
  participants create this token, which is the extra setup step).
"""

from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)

_BASE_URL = os.getenv("AIRFLOW_API_BASE_URL", "http://localhost:8080").rstrip("/")
_WAIT_TIMEOUT = 600


def _bearer_token() -> str:
    if os.getenv("ENVIRONMENT") == "astro":
        token = os.getenv("AIRFLOW_API_TOKEN")
        if not token:
            raise RuntimeError("ENVIRONMENT=astro but AIRFLOW_API_TOKEN is not set")
        return token
    response = requests.post(
        f"{_BASE_URL}/auth/token",
        json={
            "username": os.getenv("AIRFLOW_API_USERNAME", "admin"),
            "password": os.getenv("AIRFLOW_API_PASSWORD", "admin"),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_bearer_token()}"}


def trigger_dag_run(dag_id: str, conf: dict) -> str:
    response = requests.post(
        f"{_BASE_URL}/api/v2/dags/{dag_id}/dagRuns",
        headers=_auth_headers(),
        json={"logical_date": None, "conf": conf},
        timeout=30,
    )
    response.raise_for_status()
    dag_run_id = response.json()["dag_run_id"]
    log.info("triggered %s run %s", dag_id, dag_run_id)
    return dag_run_id


def wait_for_dag_run(dag_id: str, dag_run_id: str, interval: int = 1) -> str:
    response = requests.get(
        f"{_BASE_URL}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/wait",
        headers=_auth_headers(),
        params={"interval": interval},
        timeout=_WAIT_TIMEOUT,
        stream=True,
    )
    response.raise_for_status()
    for _ in response.iter_lines():
        pass
    state_response = requests.get(
        f"{_BASE_URL}/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}",
        headers=_auth_headers(),
        timeout=30,
    )
    state_response.raise_for_status()
    state = state_response.json()["state"]
    log.info("%s run %s finished: state=%s", dag_id, dag_run_id, state)
    return state


def latest_run_id(dag_id: str) -> str | None:
    response = requests.get(
        f"{_BASE_URL}/api/v2/dags/{dag_id}/dagRuns",
        headers=_auth_headers(),
        params={"order_by": "-run_after", "limit": 1},
        timeout=30,
    )
    response.raise_for_status()
    runs = response.json().get("dag_runs", [])
    return runs[0]["dag_run_id"] if runs else None
