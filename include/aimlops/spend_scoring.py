"""Shared spend-model scoring logic.

Used by spend_inference in both its modes (the single-prospect tool run and
the batch run), so on-demand and batch scoring stay identical. Pure
functions plus DuckDB reads; no Airflow task wiring lives here.
"""

from __future__ import annotations

import json

_MODEL_NAME = "spend_model"
_DEFAULT_TRIP_DAYS = 7
_AI_FEATURE_KEYS = ("trip_occasion", "enthusiasm", "budget_signal")
_CATEGORICAL = (
    "destination_planet",
    "home_planet",
    "trip_occasion",
    "enthusiasm",
    "budget_signal",
)


def load_best_model() -> dict:
    """Read the production spend_model: version, run, and trained feature columns."""
    from include.aimlops.persistence import get_duckdb_conn

    with get_duckdb_conn(read_only=True) as conn:
        row = conn.execute(
            "SELECT model_version, run_id FROM ml_models "
            "WHERE model_name = ? AND stage = 'production' "
            "ORDER BY model_version DESC LIMIT 1",
            [_MODEL_NAME],
        ).fetchone()
        if not row:
            raise ValueError(f"No production '{_MODEL_NAME}' is registered")
        model_version, run_id = row
        params_row = conn.execute(
            "SELECT hyperparameters FROM ml_runs WHERE run_id = ?", [run_id]
        ).fetchone()

    params = json.loads(params_row[0]) if params_row and params_row[0] else {}
    return {
        "model_name": _MODEL_NAME,
        "model_version": model_version,
        "run_id": run_id,
        "feature_names": params.get("features", []),
    }


def build_feature_row(prospect: dict) -> dict:
    """Build the feature row for one prospect via the training transforms.

    Deterministic features come from a synthetic single booking run through the
    same spend_features transforms as training. AI features (trip_occasion,
    enthusiasm, budget_signal) are merged only when the caller supplies them; a
    not-yet-scored customer who never emailed simply has none.
    """
    from include.aimlops.persistence import load_records
    from include.aimlops.spend_features import build_frames, compute_spend_features

    customer_id = prospect["customer_id"]
    destination = str(prospect["destination"])
    passengers = int(prospect.get("passengers") or 1)
    trip_length_days = int(prospect.get("trip_length_days") or _DEFAULT_TRIP_DAYS)
    promo_code = prospect.get("promo_code")

    planets = load_records("planets")
    routes = load_records("routes")
    dest_planet = next(
        (p for p in planets if str(p["planet_name"]).lower() == destination.lower()), None
    )
    if dest_planet is None:
        raise ValueError(f"Unknown destination planet: {destination}")
    route = next(
        (r for r in routes if r["destination_id"] == dest_planet["planet_id"]), None
    )
    if route is None:
        raise ValueError(f"No route to {destination}")

    synthetic_id = -1
    history = {
        "bookings": [
            {
                "booking_id": synthetic_id,
                "customer_id": customer_id,
                "route_id": route["route_id"],
                "passengers": passengers,
                "trip_length_days": trip_length_days,
                "promo_code": promo_code,
            }
        ],
        "payments": [
            {"booking_id": synthetic_id, "amount_usd": route["base_fare_usd"] * passengers}
        ],
        "routes": routes,
        "planets": planets,
        "customers": load_records("customers"),
        "promo_codes": load_records("promo_codes"),
        "cosmarket_orders": load_records("cosmarket_orders"),
        "menu_items": load_records("menu_items"),
    }

    frames = build_frames(history)
    features = compute_spend_features(frames).to_dicts()[0]
    for key in _AI_FEATURE_KEYS:
        value = prospect.get(key)
        if value is not None:
            features[key] = value
    return features


def score(model: dict, features: dict) -> float:
    """Realign the feature row to the model's trained columns and predict."""
    import numpy as np
    import polars as pl

    from include.mlops_tracking import MlopsTracker

    estimator = MlopsTracker().load_model(model["model_name"], stage="production")
    feature_names = model["feature_names"]

    frame = pl.DataFrame([features]).drop("booking_id")
    cat_cols = [c for c in _CATEGORICAL if c in frame.columns]
    frame = frame.to_dummies(columns=cat_cols)
    bool_cols = [c for c, t in frame.schema.items() if t == pl.Boolean]
    frame = frame.with_columns([pl.col(c).cast(pl.Int64) for c in bool_cols]).fill_null(0)
    row = frame.to_dicts()[0]

    vector = [float(row.get(name, 0)) for name in feature_names]
    return float(estimator.predict(np.array([vector]))[0])


def catering_revenue_report(
    estimates: list[dict], trips: list[dict], food_cost_ratio: float
) -> dict:
    # Project catering revenue per prospective trip (spend per person per day x
    # passengers x trip length), plus the cost and profit totals across all trips.
    estimate_by_customer = {e["customer_id"]: e for e in estimates}
    rows = []
    total_revenue = 0.0
    for customer_id, trip in sorted({t["customer_id"]: t for t in trips}.items()):
        estimate = estimate_by_customer.get(customer_id)
        if not estimate or estimate.get("food_spend_pp_pd") is None:
            continue
        pp_pd = float(estimate["food_spend_pp_pd"])
        passengers = int(trip["passengers"])
        days = int(trip["trip_length_days"])
        revenue = pp_pd * passengers * days
        total_revenue += revenue
        rows.append(
            {
                "customer_id": customer_id,
                "destination": trip["destination"],
                "passengers": passengers,
                "days": days,
                "food_spend_pp_pd": pp_pd,
                "revenue": revenue,
            }
        )
    cost = total_revenue * food_cost_ratio
    return {
        "rows": rows,
        "prospects": len(rows),
        "total_revenue": total_revenue,
        "estimated_cost": cost,
        "expected_profit": total_revenue - cost,
    }
