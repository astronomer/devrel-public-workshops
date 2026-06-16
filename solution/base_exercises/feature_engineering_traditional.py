from airflow.sdk import chain, dag, task
from include.aimlops.assets import DETERMINISTIC_FEATURES_READY

_SOURCE_TABLES = [
    "bookings",
    "payments",
    "routes",
    "planets",
    "customers",
    "promo_codes",
    "cosmarket_orders",
    "menu_items",
    "meal_orders",
]


@dag(tags=["exercise 2"])
def feature_engineering_traditional():

    @task
    def extract_history() -> dict:
        import json

        from include.aimlops.persistence import load_records

        history = {t: load_records(t) for t in _SOURCE_TABLES}
        return json.loads(json.dumps(history, default=str))

    @task
    def compute_features_and_labels(history: dict) -> dict:
        from include.aimlops.spend_features import (
            build_frames,
            compute_spend_features,
            compute_spend_labels,
        )

        frames = build_frames(history)
        return {
            "features": compute_spend_features(frames).to_dicts(),
            "labels": compute_spend_labels(frames).to_dicts(),
        }

    @task(outlets=[DETERMINISTIC_FEATURES_READY])
    def write_features(payload: dict) -> None:
        from include.aimlops.persistence import (
            get_duckdb_conn,
            replace_table,
            sync_table_to_variable,
        )
        from include.aimlops.spend_features import FEATURE_COLUMNS

        with get_duckdb_conn() as conn:
            replace_table(conn, "spend_features", FEATURE_COLUMNS, payload["features"])
            replace_table(
                conn,
                "spend_labels",
                ["booking_id", "food_spend_pp_pd"],
                payload["labels"],
            )

        sync_table_to_variable("spend_features")
        sync_table_to_variable("spend_labels")

    _history = extract_history()
    _features = compute_features_and_labels(_history)
    _written = write_features(_features)
    chain(_history, _features, _written)


feature_engineering_traditional()