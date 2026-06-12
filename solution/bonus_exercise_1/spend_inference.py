import json
from datetime import datetime

from airflow.sdk import Param, chain, dag, task

_FOOD_COST_RATIO = 0.55


@dag(
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    params={"prospect": Param({}, type="object")},
    tags=["Bonus exercise 1"],
    doc_md=__doc__,
)
def spend_inference():

    @task
    def load_best_model() -> dict:
        from include.aimlops import spend_scoring

        return spend_scoring.load_best_model()

    @task
    def select_targets() -> list[dict]:
        from airflow.sdk import get_current_context

        from include.aimlops.persistence import load_records

        prospect = get_current_context()["params"].get("prospect") or {}
        if prospect:
            return [prospect]
        return load_records("prospective_trips")

    @task(max_active_tis_per_dagrun=1)
    def score_target(model: dict, target: dict) -> dict:
        from include.aimlops import spend_scoring

        features = spend_scoring.build_feature_row(target)
        estimate = spend_scoring.score(model, features)
        return {
            "customer_id": target.get("customer_id"),
            "food_spend_pp_pd": estimate,
            "model_name": model["model_name"],
            "model_version": model["model_version"],
        }

    @task.branch
    def route_by_mode() -> str:
        from airflow.sdk import get_current_context

        prospect = get_current_context()["params"].get("prospect") or {}
        return "record_prediction" if prospect else "write_estimates"

    @task
    def record_prediction(scores: list[dict]) -> float:
        from airflow.sdk import get_current_context

        from include.aimlops.persistence import get_duckdb_conn

        context = get_current_context()
        run_id = context["run_id"]
        prospect = context["params"].get("prospect", {})
        score = scores[0]
        with get_duckdb_conn() as conn:
            conn.execute("DELETE FROM spend_predictions WHERE dag_run_id = ?", [run_id])
            conn.execute(
                "INSERT INTO spend_predictions "
                "(dag_run_id, prospect, food_spend_pp_pd, model_name, model_version) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    run_id,
                    json.dumps(prospect),
                    score["food_spend_pp_pd"],
                    score["model_name"],
                    score["model_version"],
                ],
            )
        return score["food_spend_pp_pd"]

    @task
    def write_estimates(scores: list[dict]) -> None:
        from include.aimlops.persistence import get_duckdb_conn, replace_table, sync_table_to_variable

        columns = ["customer_id", "food_spend_pp_pd", "model_name", "model_version"]
        with get_duckdb_conn() as conn:
            replace_table(conn, "customer_spend_estimates", columns, scores)
        sync_table_to_variable("customer_spend_estimates")

    @task
    def report_estimates() -> dict:
        import logging

        from include.aimlops.persistence import load_records
        from include.aimlops.spend_scoring import catering_revenue_report

        log = logging.getLogger("airflow.task")
        report = catering_revenue_report(
            load_records("customer_spend_estimates"),
            load_records("prospective_trips"),
            _FOOD_COST_RATIO,
        )

        log.info("Expected catering across %d prospective trips:", report["prospects"])
        log.info(
            "  %-9s %-8s %4s %5s %11s %14s",
            "customer", "dest", "pax", "days", "$pp/day", "trip $",
        )
        for r in report["rows"]:
            log.info(
                "  %-9s %-8s %4d %5d %11.2f %14.2f",
                r["customer_id"], r["destination"], r["passengers"], r["days"],
                r["food_spend_pp_pd"], r["revenue"],
            )
        log.info("  total expected food revenue:       $%s", f"{report['total_revenue']:,.2f}")
        log.info(
            "  estimated catering cost (%d%% food cost): $%s",
            int(_FOOD_COST_RATIO * 100), f"{report['estimated_cost']:,.2f}",
        )
        log.info("  expected catering profit:          $%s", f"{report['expected_profit']:,.2f}")

        return {
            "prospects": report["prospects"],
            "total_revenue": round(report["total_revenue"], 2),
            "estimated_cost": round(report["estimated_cost"], 2),
            "expected_profit": round(report["expected_profit"], 2),
        }

    _model = load_best_model()
    _targets = select_targets()
    _scores = score_target.partial(model=_model).expand(target=_targets)

    _route = route_by_mode()
    _prediction = record_prediction(_scores)
    _written = write_estimates(_scores)
    _report = report_estimates()

    chain(_scores, _route, [_prediction, _written])
    chain(_written, _report)


spend_inference()
