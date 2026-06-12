from datetime import datetime, timedelta

from airflow.sdk import chain, dag, task

from include.aimlops.assets import MODEL_REGISTERED, PLUGIN_SYNC

_EXPERIMENT = "food_spend_prediction"
_MODEL_NAME = "spend_model"

_N_ESTIMATORS = [200]
_MAX_DEPTH = [6]

_LR_ALPHA = [0.1, 0.5]
_LR_L1_RATIO = [0.2, 0.5]


@dag(
    start_date=datetime(2026, 1, 1),
    schedule=None,
    tags=["exercise 2"],
    max_active_tasks=1,  # local db only allows one concurrent write
    default_args={"retries": 3, "retry_delay": timedelta(seconds=10)},
    doc_md=__doc__,
)
def train_spend_model():

    @task
    def assemble_training_set() -> dict:
        import polars as pl

        from include.aimlops.persistence import load_records
        from include.aimlops.spend_features import one_hot_encode
        categorical_cols = ["destination_planet", "home_planet"]

        df = pl.DataFrame(load_records("spend_features")).join(
            pl.DataFrame(load_records("spend_labels")), on="booking_id", how="inner"
        )

        # After you complete exercise 3 this part will read in the AI-generated features
        ai_records = load_records("ai_features")
        use_ai = len(ai_records) > 0
        if use_ai:
            df = df.join(pl.DataFrame(ai_records), on="booking_id", how="left")
            categorical_cols += ["trip_occasion", "enthusiasm", "budget_signal"]

        df = one_hot_encode(df, categorical_cols)

        y = df["food_spend_pp_pd"].to_list()
        X = df.drop("booking_id", "food_spend_pp_pd")
        return {
            "feature_names": X.columns,
            "X": X.to_numpy().tolist(),
            "y": y,
            "feature_set": "ai" if use_ai else "deterministic",
        }

    @task(max_active_tis_per_dagrun=1)  # local db only allows one concurrent write
    def train_random_forest(n_estimators: int, max_depth: int, training_set: dict) -> dict:
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        from include.aimlops.training import evaluate_regression
        from include.mlops_tracking import MlopsTracker

        X = np.array(training_set["X"], dtype=float)
        y = np.array(training_set["y"], dtype=float)
        feature_set = training_set["feature_set"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model = RandomForestRegressor(
            n_estimators=n_estimators, max_depth=max_depth, random_state=42
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        params = {
            "model_type": "RandomForestRegressor",
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "features": training_set["feature_names"],
            "feature_set": feature_set,
            "enriched": feature_set == "ai",
            "test_size": 0.2,
            "random_state": 42,
            "feature_importances": dict(
                zip(training_set["feature_names"], model.feature_importances_.tolist())
            ),
        }
        metrics = {
            **evaluate_regression(y_test, preds),
            "train_size": len(X_train),
            "test_size": len(X_test),
        }

        model_name = f"{_MODEL_NAME}_random_forest_regressor"
        tracker = MlopsTracker()
        run_id = tracker.start_run(
            experiment_name=_EXPERIMENT,
            dag_id="train_spend_model",
            task_id="train_variant",
            tags={"feature_set": feature_set, "n_estimators": n_estimators, "max_depth": max_depth},
        )
        tracker.log_params(run_id, params)
        tracker.log_metrics(run_id, metrics)
        model_version = tracker.log_model(run_id, model_name, "RandomForestRegressor", model)
        tracker.end_run(run_id)

        return {
            "run_id": run_id,
            "model_name": model_name,
            "model_version": model_version,
            "model_type": "RandomForestRegressor",
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "rmse": metrics["rmse"],
            "r2": metrics["r2"],
            "metrics": metrics,
            "params": params,
            "feature_cols": training_set["feature_names"],
            "importances": model.feature_importances_.tolist(),
            "importance_label": "Importance",
            "y_test": y_test.tolist(),
            "y_pred": preds.tolist(),
        }

    @task(max_active_tis_per_dagrun=1)
    def train_linear(alpha: float, l1_ratio: float, training_set: dict) -> dict:
        import numpy as np
        from sklearn.linear_model import ElasticNet
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        from include.aimlops.training import evaluate_regression
        from include.mlops_tracking import MlopsTracker

        X = np.array(training_set["X"], dtype=float)
        y = np.array(training_set["y"], dtype=float)
        feature_set = training_set["feature_set"]
        feature_names = training_set["feature_names"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("elasticnet", ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=42)),
            ]
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        en = model.named_steps["elasticnet"]
        params = {
            "model_type": "ElasticNet",
            "alpha": alpha,
            "l1_ratio": l1_ratio,
            "features": feature_names,
            "feature_set": feature_set,
            "enriched": feature_set == "ai",
            "test_size": 0.2,
            "random_state": 42,
            "coefficients": dict(zip(feature_names, en.coef_.tolist())),
            "intercept": float(en.intercept_),
        }
        metrics = {
            **evaluate_regression(y_test, preds),
            "train_size": len(X_train),
            "test_size": len(X_test),
        }

        model_name = f"{_MODEL_NAME}_elastic_net"
        tracker = MlopsTracker()
        run_id = tracker.start_run(
            experiment_name=_EXPERIMENT,
            dag_id="train_spend_model",
            task_id="train_linear",
            tags={"feature_set": feature_set, "alpha": alpha, "l1_ratio": l1_ratio},
        )
        tracker.log_params(run_id, params)
        tracker.log_metrics(run_id, metrics)
        model_version = tracker.log_model(run_id, model_name, "ElasticNet", model)
        tracker.end_run(run_id)

        return {
            "run_id": run_id,
            "model_name": model_name,
            "model_version": model_version,
            "model_type": "ElasticNet",
            "alpha": alpha,
            "l1_ratio": l1_ratio,
            "rmse": metrics["rmse"],
            "r2": metrics["r2"],
            "metrics": metrics,
            "params": params,
            "feature_cols": feature_names,
            "importances": en.coef_.tolist(),
            "importance_label": "Coefficient",
            "y_test": y_test.tolist(),
            "y_pred": preds.tolist(),
        }

    @task
    def select_best(forest_variants: list[dict], linear_variants: list[dict]) -> dict:
        return min([*forest_variants, *linear_variants], key=lambda v: v["rmse"])

    @task
    def visualize(best: dict) -> dict:
        from include.aimlops.training import describe_model
        from include.ml_plots import plot_regression
        from include.mlops_tracking import MlopsTracker

        title = (
            f"Food Spend per Day per Person | {describe_model(best)} | "
            f"R2 = {best['metrics']['r2']:.3f}, RMSE = {best['metrics']['rmse']:.2f}"
        )
        return plot_regression({**best, "plot_title": title}, MlopsTracker())

    @task(outlets=[MODEL_REGISTERED, PLUGIN_SYNC])
    def register_model(best: dict) -> None:
        from include.mlops_tracking import MlopsTracker

        MlopsTracker().promote_model(best["model_name"], best["model_version"], stage="production")



    _set = assemble_training_set()
    _forest = train_random_forest.partial(training_set=_set).expand(
        n_estimators=_N_ESTIMATORS, max_depth=_MAX_DEPTH
    )
    _linear = train_linear.partial(training_set=_set).expand(
        alpha=_LR_ALPHA, l1_ratio=_LR_L1_RATIO
    )
    _best = select_best(_forest, _linear)
    _plot = visualize(_best)
    _registered = register_model(_best)
    chain(_set, [_forest, _linear], _best, _plot, _registered)


train_spend_model()
