"""
Dag to predict which dessert a customer will order using a RandomForestClassifier.

Dessert classes:
  21 = Ktarian Chocolate Puff
  22 = Blue Jello
  23 = Bob's Raisin Cookies
  24 = Seldon's Psychohistory Swirl
  25 = Sweet Kibble
"""

import logging
import os

from airflow.sdk import Asset, dag, task, chain
from include.mission_control import MissionControlOperator

log = logging.getLogger("airflow.task")

_DATA_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_EXPERIMENT = "dessert_prediction"


@dag(
    schedule=None,
    tags=["classification"],
    max_active_tasks=1,  # avoiding parallel writes to the duckdb database
    doc_md=__doc__,
)
def space_dessert_classification():

    @task
    def extract() -> dict:
        import duckdb
        import pandas as pd
        from airflow.sdk.bases.hook import BaseHook
        from include.ml_queries import (
            CLASSIFICATION_BASE_QUERY,
            CLASSIFICATION_ENRICHED_QUERY,
            features_available,
        )

        db_path = BaseHook.get_connection(_DATA_CONN_ID).host
        conn = duckdb.connect(db_path, read_only=True)
        enriched = features_available(conn)
        query = CLASSIFICATION_ENRICHED_QUERY if enriched else CLASSIFICATION_BASE_QUERY
        df = pd.read_sql(query, conn)
        conn.close()
        log.info("Extracted %d dessert orders (enriched=%s).", len(df), enriched)
        return {"data": df.to_dict(orient="list"), "enriched": enriched}

    @task
    def train(payload: dict) -> dict:
        import base64
        import json
        import pickle

        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from include.mlops_tracking import MlopsTracker

        df = pd.DataFrame(payload["data"])
        enriched = payload["enriched"]

        if enriched:
            feature_cols = [
                "passengers", "trip_length", "base_multiplier",
                "has_children", "child_ratio", "has_promo",
                "is_business", "is_gold", "is_silver",
                "is_gemini", "is_claude", "is_chatgpt", "is_llama",
                "is_high_orbit", "is_low_orbit",
                "is_all_inclusive", "is_budget_plan",
                "c_gemini_highorbit_allinc_biz", "c_chatgpt_gold_kids", "c_llama_loworbit_budget_promo",
                "c_claude_highorbit_allinc_nokids", "c_llama_loworbit_budget_nogold",
            ]
        else:
            feature_cols = [
                "passengers", "trip_length", "base_multiplier",
            ]

        X = df[feature_cols].values.astype(float)
        y = df["dessert_id"].values.astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        model_config = {
            "n_estimators": 200,
            "max_depth": 15,
            "random_state": 42,
        }

        model = RandomForestClassifier(**model_config)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
        }
        params = {
            "model_type": "RandomForestClassifier",
            **model_config,
            "features": feature_cols,
            "enriched": enriched,
        }

        tracker = MlopsTracker()
        run_id = tracker.start_run(
            experiment_name=_EXPERIMENT,
            dag_id="space_dessert_classification",
            task_id="train",
            description="Predict which dessert a customer orders",
            tags={"enriched": enriched},
        )
        tracker.log_params(run_id, params)
        tracker.log_metrics(run_id, metrics)
        model_version = tracker.log_model(
            run_id, "dessert_predictor", "RandomForestClassifier", model,
        )

        log.info("Classification metrics (enriched=%s): %s", enriched, json.dumps(metrics, indent=2))

        return {
            "experiment": _EXPERIMENT,
            "run_id": run_id,
            "dag_id": "space_dessert_classification",
            "metrics": metrics,
            "params": params,
            "model_name": "dessert_predictor",
            "model_type": "RandomForestClassifier",
            "model_version": model_version,
            "model_b64": base64.b64encode(pickle.dumps(model)).decode("utf-8"),
            "y_test": y_test.tolist(),
            "y_pred": y_pred.tolist(),
            "feature_cols": feature_cols,
            "feature_importances": model.feature_importances_.tolist(),
        }

    @task
    def visualize(results: dict) -> dict:
        from include.ml_plots import plot_classification
        from include.mlops_tracking import MlopsTracker

        return plot_classification(results, MlopsTracker())

    @task(outlets=[Asset("plugin_sync")])
    def promote(results: dict):
        from include.mlops_tracking import MlopsTracker

        tracker = MlopsTracker()
        tracker.promote_model(
            results["model_name"], results["model_version"],
        )
        log.info(
            "Promoted %s v%s to production (accuracy=%.4f)",
            results["model_name"], results["model_version"],
            results["metrics"]["accuracy"],
        )

    _mission_control = MissionControlOperator(task_id="mission_control")

    _extract = extract()
    _train = train(_extract)
    _visualize = visualize(_train)
    _promote = promote(_train)
    chain(_visualize, _promote, _mission_control)


space_dessert_classification()
