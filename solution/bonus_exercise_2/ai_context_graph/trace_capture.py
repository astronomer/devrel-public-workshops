import json
import logging

from airflow.sdk import chain, dag, task

from include.aimlops.assets import INTERACTION_COMPLETE, TRACE_CREATED

log = logging.getLogger(__name__)
_SOURCE_DAG = "respond_to_email"


def _source_run_id(context) -> str | None:
    for asset_events in (context.get("triggering_asset_events") or {}).values():
        for event in asset_events:
            if event.source_run_id:
                return event.source_run_id
    return None


def _latest_source_run_id() -> str | None:
    from include.airflow_api import latest_run_id

    return latest_run_id(_SOURCE_DAG)


def assemble_trace(step_data: dict) -> dict:
    thread = step_data.get("thread") or {}
    draft = step_data.get("draft") or {}
    verdict = step_data.get("verdict") or {}
    human = step_data.get("human") or {}
    revised = step_data.get("revised") or {}

    thread_id = thread.get("thread_id")
    turn = thread.get("next_turn")

    chosen = human.get("chosen_options", []) if isinstance(human, dict) else []
    choice = chosen[0] if chosen else "unknown"
    reason = (human.get("params_input") or {}).get("reason", "") if isinstance(human, dict) else ""

    last_inbound = next(
        (m for m in reversed(thread.get("messages", [])) if m.get("direction") == "inbound"),
        None,
    )

    steps = [
        {
            "step": "agent draft",
            "decision_maker": {"type": "ai", "agent": "drafter"},
            "logic": {"reasoning": draft.get("reasoning", "")},
            "output": {"email": draft.get("email", "")},
        },
        {
            "step": "ai judge",
            "decision_maker": {"type": "ai", "agent": "judge"},
            "logic": {"reasoning": verdict.get("reasoning", "")},
            "output": {"grade": verdict.get("grade"), "issues": verdict.get("issues", [])},
        },
        {
            "step": "human review",
            "decision_maker": {"type": "human"},
            "logic": {"explanation": reason},
            "output": {"decision": choice},
        },
    ]
    if revised:
        steps.append(
            {
                "step": "agent rewrite",
                "decision_maker": {"type": "ai", "agent": "drafter"},
                "logic": {"reasoning": revised.get("reasoning", "")},
                "output": {"email": revised.get("email", "")},
            }
        )

    return {
        "trace_id": f"dt-thread{thread_id}-turn{turn}",
        "entity_references": {
            "thread_id": thread_id,
            "turn": turn,
            "customer_id": thread.get("customer_id"),
        },
        "inputs": {
            "user_request": last_inbound.get("body") if last_inbound else None,
            "subject": thread.get("subject"),
        },
        "context_used": draft.get("context_used", []),
        "steps": steps,
        "outcome": {"status": "sent" if choice in ("approve", "rewrite") else "rejected"},
    }


@dag(
    schedule=[INTERACTION_COMPLETE],
    catchup=False,
    tags=["Bonus exercise 2"],
)
def trace_capture():

    @task
    def pull_step_data() -> dict:
        from airflow.sdk import get_current_context

        context = get_current_context()
        ti = context["ti"]
        run_id = _source_run_id(context) or _latest_source_run_id()
        log.info("trace_capture reading %s run_id=%s", _SOURCE_DAG, run_id)
        task_ids = {
            "thread": "load_thread",
            "draft": "draft_reply",
            "verdict": "judge_reply",
            "human": "human_in_the_loop",
            "revised": "revise_reply",
        }
        return {
            key: ti.xcom_pull(dag_id=_SOURCE_DAG, task_ids=task_id, run_id=run_id)
            for key, task_id in task_ids.items()
        }

    @task
    def build_trace(step_data: dict) -> dict:
        return assemble_trace(step_data)

    @task(outlets=[TRACE_CREATED])
    def write_trace(trace: dict) -> None:
        from include.aimlops.persistence import get_duckdb_conn, sync_table_to_variable

        conn = get_duckdb_conn()
        conn.execute("DELETE FROM decision_traces WHERE trace_id = ?", [trace["trace_id"]])
        conn.execute(
            "INSERT INTO decision_traces "
            "(trace_id, entity_references, inputs, context_used, steps, outcome) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                trace["trace_id"],
                json.dumps(trace["entity_references"]),
                json.dumps(trace["inputs"]),
                json.dumps(trace["context_used"]),
                json.dumps(trace["steps"]),
                json.dumps(trace["outcome"]),
            ],
        )
        conn.close()
        sync_table_to_variable("decision_traces")

    _data = pull_step_data()
    _trace = build_trace(_data)
    _written = write_trace(_trace)
    chain(_data, _trace, _written)


trace_capture()
