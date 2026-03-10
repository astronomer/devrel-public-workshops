"""
Dag to predict daily catering revenue.
"""

import logging
import os

from airflow.sdk import dag, task

log = logging.getLogger("airflow.task")

_DATA_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_EXPERIMENT = "daily_catering_revenue"

_MODEL_CONFIGS = [
    {"model_type": "DecisionTreeRegressor", "max_depth": 2},
    {"model_type": "LinearRegression"},
    {"model_type": "Ridge", "alpha": 10.0},
    {"model_type": "GradientBoostingRegressor", "n_estimators": 200, "max_depth": 10},
]


def _model_name_for(model_type: str) -> str:
    """Derive a registry-friendly model name from a sklearn class name."""
    import re
    snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", model_type).lower()
    return f"catering_revenue_{snake}"


def _build_model(config: dict):
    """Create a sklearn model instance from a config dict."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.tree import DecisionTreeRegressor

    model_type = config["model_type"]
    if model_type == "LinearRegression":
        return LinearRegression()
    if model_type == "Ridge":
        return Ridge(alpha=config.get("alpha", 1.0))
    if model_type == "DecisionTreeRegressor":
        return DecisionTreeRegressor(
            max_depth=config.get("max_depth", None),
            random_state=42,
        )
    if model_type == "GradientBoostingRegressor":
        return GradientBoostingRegressor(
            n_estimators=config.get("n_estimators", 100),
            max_depth=config.get("max_depth", 3),
            random_state=42,
        )
    raise ValueError(f"Unknown model type: {model_type}")


@dag(
    schedule=None,
    tags=["regression"],
    max_active_tasks=1,  # avoiding parallel writes to the duckdb database
    doc_md=__doc__,
)
def astro_trip_catering_revenue_prediction():

    @task
    def extract() -> dict:
        import duckdb
        import pandas as pd
        from airflow.sdk.bases.hook import BaseHook
        from include.ml_queries import (
            REGRESSION_BASE_QUERY,
            REGRESSION_ENRICHED_QUERY,
            features_available,
        )

        db_path = BaseHook.get_connection(_DATA_CONN_ID).host
        conn = duckdb.connect(db_path, read_only=True)
        enriched = features_available(conn)
        query = REGRESSION_ENRICHED_QUERY if enriched else REGRESSION_BASE_QUERY
        df = pd.read_sql(query, conn)
        conn.close()
        log.info("Extracted %d rows (enriched=%s).", len(df), enriched)
        return {"data": df.to_dict(orient="list"), "enriched": enriched}

    @task
    def train(payload: dict, config: dict) -> dict:
        import base64
        import json
        import pickle

        import numpy as np
        import pandas as pd
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split
        from include.mlops_tracking import MlopsTracker

        df = pd.DataFrame(payload["data"])
        enriched = payload["enriched"]

        if enriched:
            feature_cols = [
                "passengers",
                "trip_length",
                "base_multiplier",
                "is_business",
                "is_gold",
                "is_silver",
                "has_promo",

                "has_children",
                "child_ratio",
                "is_gemini", "is_claude", "is_chatgpt", "is_llama",
                "is_high_orbit", "is_low_orbit",
                "is_all_inclusive", "is_budget_plan",
                "c_gemini_highorbit_allinc_biz",
            ]
        else:
            feature_cols = [
                "passengers",
                "trip_length",
                "base_multiplier",
            ]

        X = df[feature_cols].values.astype(float)
        y = df["daily_spend"].values.astype(float)
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )

        model_type = config["model_type"]
        model = _build_model(config)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            "rmse": float(
                np.sqrt(mean_squared_error(y_test, y_pred))
            ),  # root mean squared error (lower is better)
            "mae": float(
                mean_absolute_error(y_test, y_pred)
            ),  # mean absolute error (lower is better)
            "r2": float(r2_score(y_test, y_pred)),  # R-squared score (higher is better)
            "train_size": int(len(X_train)),  # number of rows in the training set
            "test_size": int(len(X_test)),  # number of rows in the test set
        }
        params = {
            "model_type": model_type,
            "features": feature_cols,
            "enriched": enriched,
            "test_size": 0.2,
            "random_state": 42,
            **{k: v for k, v in config.items() if k != "model_type"},
        }

        # get coefficients or feature importances depending on the model type
        # these are to determine which aspects of the data are most important to the model
        if hasattr(model, "coef_"):
            importances = model.coef_.tolist()
            importance_label = "Coefficient"
        elif hasattr(model, "feature_importances_"):
            importances = model.feature_importances_.tolist()
            importance_label = "Importance"
        else:
            importances = [0.0] * len(feature_cols)
            importance_label = "Importance"

        # the tracker is used to log the metrics, parameters, and model to the MLOps tracking system
        tracker = MlopsTracker()
        run_id = tracker.start_run(
            experiment_name=_EXPERIMENT,
            dag_id="astro_trip_catering_revenue_prediction",
            task_id="train",
            description=f"Revenue prediction with {model_type}",
            tags={"enriched": enriched, "model_type": model_type},
        )
        tracker.log_params(run_id, params)
        tracker.log_metrics(run_id, metrics)
        model_name = _model_name_for(model_type)
        model_version = tracker.log_model(
            run_id,
            model_name,
            model_type,
            model,
        )

        log.info(
            "%s metrics (enriched=%s): %s",
            model_type,
            enriched,
            json.dumps(metrics, indent=2),
        )

        return {
            "experiment": _EXPERIMENT,
            "run_id": run_id,
            "dag_id": "astro_trip_catering_revenue_prediction",
            "metrics": metrics,
            "params": params,
            "model_name": model_name,
            "model_type": model_type,
            "model_version": model_version,
            "model_b64": base64.b64encode(pickle.dumps(model)).decode("utf-8"),
            "y_test": y_test.tolist(),
            "y_pred": y_pred.tolist(),
            "feature_cols": feature_cols,
            "importances": importances,
            "importance_label": importance_label,
        }

    @task
    def visualize(results: dict) -> dict:
        from include.ml_plots import plot_regression
        from include.mlops_tracking import MlopsTracker

        return plot_regression(results, MlopsTracker())

    @task
    def promote(results: list[dict]):
        from include.mlops_tracking import MlopsTracker

        best = max(results, key=lambda r: r["metrics"]["r2"])
        other_names = list(
            set(r["model_name"] for r in results) - {best["model_name"]}
        )
        tracker = MlopsTracker()
        tracker.promote_model(
            best["model_name"], best["model_version"],
            related_names=other_names,
        )
        log.info(
            "Promoted %s v%s to production (R²=%.4f, type=%s)",
            best["model_name"], best["model_version"],
            best["metrics"]["r2"], best["model_type"],
        )

    _extract = extract()
    _train = train.partial(payload=_extract).expand(config=_MODEL_CONFIGS)
    _visualize = visualize.expand(results=_train)
    _promote = promote(_train)


astro_trip_catering_revenue_prediction()
