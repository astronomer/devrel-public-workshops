from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_regression(y_true, y_pred) -> dict:
    # Standard regression scores: RMSE and MAE (lower is better), R2 (higher is better).
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def describe_model(result: dict) -> str:
    # Human-readable model label with its key hyperparameters, for plot titles.
    model_type = result["model_type"]
    if model_type == "RandomForestRegressor":
        return (
            f"RandomForestRegressor (n_estimators={result['n_estimators']}, "
            f"max_depth={result['max_depth']})"
        )
    if model_type == "ElasticNet":
        return f"ElasticNet (alpha={result['alpha']}, l1_ratio={result['l1_ratio']})"
    return model_type
