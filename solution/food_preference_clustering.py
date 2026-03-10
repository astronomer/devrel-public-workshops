"""
Dag to cluster customers by their dining behavior.
"""

import logging
import os

from airflow.sdk import dag, task

log = logging.getLogger("airflow.task")

_DATA_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_EXPERIMENT = "culinary_personas"


@dag(
    schedule=None,
    tags=["clustering"],
    max_active_tasks=1,  # avoiding parallel writes to the duckdb database
    doc_md=__doc__,
)
def food_preference_clustering():

    @task
    def extract() -> dict:
        import duckdb
        import pandas as pd
        from airflow.sdk.bases.hook import BaseHook
        from include.ml_queries import (
            CLUSTERING_BASE_QUERY,
            CLUSTERING_ENRICHED_QUERY,
            features_available,
        )

        db_path = BaseHook.get_connection(_DATA_CONN_ID).host
        conn = duckdb.connect(db_path, read_only=True)
        enriched = features_available(conn)
        query = CLUSTERING_ENRICHED_QUERY if enriched else CLUSTERING_BASE_QUERY
        df = pd.read_sql(query, conn)
        conn.close()
        log.info("Extracted %d customers (enriched=%s).", len(df), enriched)
        return {"data": df.to_dict(orient="list"), "enriched": enriched}

    @task
    def train(payload: dict) -> dict:
        import base64
        import json
        import pickle

        import pandas as pd
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler
        from include.mlops_tracking import MlopsTracker

        df = pd.DataFrame(payload["data"])
        enriched = payload.get("enriched", False)

        if enriched:
            feature_cols = [
                "total_orders", "avg_price", "total_spend",
                "avg_child_ratio",
                "avg_is_all_inclusive", "avg_is_budget_plan",
                "avg_is_high_orbit", "avg_is_low_orbit",
            ]
        else:
            feature_cols = ["total_orders", "avg_price", "total_spend"]
        n_clusters = 3

        X = df[feature_cols].values.astype(float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(X_scaled)
        sil = float(silhouette_score(X_scaled, labels))

        cluster_profiles = {}
        for c in range(n_clusters):
            mask = labels == c
            profile = {"size": int(mask.sum())}
            for col in feature_cols:
                profile[f"avg_{col}"] = float(df.loc[mask, col].mean())
            cluster_profiles[f"cluster_{c}"] = profile

        metrics = {
            "silhouette_score": sil,
            "inertia": float(model.inertia_),
            "n_clusters": n_clusters,
            "n_customers": int(len(df)),
            **{
                f"cluster_{c}_size": int((labels == c).sum()) for c in range(n_clusters)
            },
        }
        params = {
            "model_type": "KMeans",
            "n_clusters": n_clusters,
            "features": feature_cols,
            "scaling": "StandardScaler",
            "enriched": enriched,
            "random_state": 42,
        }

        tracker = MlopsTracker()
        run_id = tracker.start_run(
            experiment_name=_EXPERIMENT,
            dag_id="food_preference_clustering",
            task_id="train",
            description="Segment customers by dining behavior",
            tags={"n_clusters": n_clusters, "enriched": enriched},
        )
        tracker.log_params(run_id, params)
        tracker.log_metrics(run_id, metrics)
        model_version = tracker.log_model(
            run_id,
            "persona_model",
            "KMeans+StandardScaler",
            {"kmeans": model, "scaler": scaler},
        )

        log.info(
            "Clustering metrics: %s",
            json.dumps(metrics, indent=2),
        )

        return {
            "experiment": _EXPERIMENT,
            "run_id": run_id,
            "dag_id": "food_preference_clustering",
            "metrics": metrics,
            "params": params,
            "model_name": "persona_model",
            "model_type": "KMeans+StandardScaler",
            "model_version": model_version,
            "model_b64": base64.b64encode(
                pickle.dumps({"kmeans": model, "scaler": scaler})
            ).decode("utf-8"),
            "labels": labels.tolist(),
            "feature_cols": feature_cols,
            "n_clusters": n_clusters,
            "cluster_profiles": cluster_profiles,
            "df_for_plot": {
                "avg_meal_spend": (df["total_spend"] / df["n_meals"].clip(lower=1)).tolist(),
                "spend_per_passenger": (df["total_spend"] / df["passengers"].clip(lower=1)).tolist(),
            },
        }

    @task
    def visualize(results: dict) -> dict:
        from include.ml_plots import plot_clustering
        from include.mlops_tracking import MlopsTracker

        return plot_clustering(results, MlopsTracker())

    @task
    def promote(results: dict):
        from include.mlops_tracking import MlopsTracker

        tracker = MlopsTracker()
        tracker.promote_model(
            results["model_name"], results["model_version"],
        )
        log.info(
            "Promoted %s v%s to production (silhouette=%.4f)",
            results["model_name"], results["model_version"],
            results["metrics"]["silhouette_score"],
        )

    _extract = extract()
    _train = train(_extract)
    _visualize = visualize(_train)
    _promote = promote(_train)


food_preference_clustering()
