#!/usr/bin/env python3
"""
Generate pre-seeded ML tracking data as CSV files.

Run this script ONCE before committing. It:
  1. Creates a temporary DuckDB with AstroTrips + food data
  2. Runs feature engineering
  3. Trains multiple iterations of each ML pipeline (raw → enriched progression)
  4. Writes experiment/run/model/plot results as CSV files to include/seed/

Usage:
    cd devrel-public-workshops
    python scripts/preseed_ml_data.py
"""

import base64
import io
import json
import os
import pickle
from datetime import datetime, timedelta

import duckdb
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..")
SQL_DIR = os.path.join(PROJECT_DIR, "include", "sql")
SEED_DIR = os.path.join(PROJECT_DIR, "include", "seed")

experiments_rows = []
runs_rows = []
models_rows = []
plots_rows = []

_next_exp = 0
_next_run = 0
_next_plot = 0
_model_counters = {}  # per-model-name versioning

_BASE_TS = datetime(2026, 2, 10, 9, 0, 0)


def _ts(day_offset=0, minute_offset=0):
    return (_BASE_TS + timedelta(days=day_offset, minutes=minute_offset)).isoformat()


def _exp_id():
    global _next_exp; _next_exp += 1; return _next_exp


def _run_id():
    global _next_run; _next_run += 1; return _next_run


def _model_ver(model_name: str):
    _model_counters[model_name] = _model_counters.get(model_name, 0) + 1
    return _model_counters[model_name]


def _plot_id():
    global _next_plot; _next_plot += 1; return _next_plot


_run_number_counters = {}


def _run_number(experiment_id: int):
    _run_number_counters[experiment_id] = _run_number_counters.get(experiment_id, 0) + 1
    return _run_number_counters[experiment_id]


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return b64


def run_sql_file(con, filename):
    with open(os.path.join(SQL_DIR, filename)) as f:
        con.execute(f.read())
    print(f"  executed {filename}")


DESSERT_NAMES = {
    21: "Ktarian Choc. Puff", 22: "Blue Jello", 23: "Bob's Raisin Cookies",
    24: "Seldon's Swirl", 25: "Sweet Kibble",
}

# ---------------------------------------------------------------------------
# Regression iterations
# ---------------------------------------------------------------------------

def _reg_base_query():
    return """
        SELECT
            mo.booking_id, mo.trip_day,
            sum(mi.price_usd * mo.quantity) AS daily_spend,
            max(b.passengers) AS passengers,
            max(b.return_date - b.departure_date) AS trip_length,
            max(p.base_multiplier) AS base_multiplier
        FROM meal_orders mo
        JOIN menu_items mi ON mo.item_id = mi.item_id
        JOIN bookings b ON mo.booking_id = b.booking_id
        JOIN routes r ON b.route_id = r.route_id
        JOIN planets p ON r.destination_id = p.planet_id
        GROUP BY mo.booking_id, mo.trip_day
    """


REGRESSION_ITERS = [
    {"features": ["passengers", "trip_length", "base_multiplier"],
     "enriched": False, "tag": "baseline – 3 raw features", "day": 0},
]


def seed_regression(con):
    print("\n--- Regression: Daily Catering Revenue (1 baseline run) ---")

    df_base = con.execute(_reg_base_query()).fetchdf()

    eid = _exp_id()
    experiments_rows.append({
        "experiment_id": eid, "experiment_name": "daily_catering_revenue",
        "description": "Predict total catering spend per booking-day",
        "created_at": _ts(0),
    })

    for i, it in enumerate(REGRESSION_ITERS):
        feats = it["features"]
        X = df_base[feats].values.astype(float)
        y = df_base["daily_spend"].values.astype(float)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "r2": float(r2_score(y_test, y_pred)),
            "train_size": int(len(X_train)), "test_size": int(len(X_test)),
        }
        params = {"model_type": "LinearRegression", "features": feats,
                   "enriched": it["enriched"], "test_size": 0.2, "random_state": 42}

        rid = _run_id(); rn = _run_number(eid); mv = _model_ver("catering_revenue_linear_regression")
        is_last = i == len(REGRESSION_ITERS) - 1

        runs_rows.append({
            "run_id": rid, "experiment_id": eid, "run_number": rn,
            "dag_id": "astro_trip_catering_revenue_prediction", "task_id": "train",
            "run_ts": _ts(it["day"], 30), "status": "COMPLETED",
            "hyperparameters": json.dumps(params), "metrics": json.dumps(metrics),
            "tags": json.dumps({"iteration": it["tag"], "enriched": it["enriched"]}),
        })
        models_rows.append({
            "model_name": "catering_revenue_linear_regression", "model_version": mv,
            "run_id": rid, "model_type": "LinearRegression",
            "model_blob": base64.b64encode(pickle.dumps(model)).decode(),
            "stage": "production" if is_last else ("staging" if i == len(REGRESSION_ITERS) - 2 else "archived"),
            "registered_at": _ts(it["day"], 31),
        })

        if i == 0 or is_last:
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            axes[0].scatter(y_test, y_pred, alpha=0.4, s=10, color="#4A90D9")
            lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
            axes[0].plot(lims, lims, "r--", linewidth=1)
            axes[0].set_xlabel("Actual Daily Spend"); axes[0].set_ylabel("Predicted"); axes[0].set_title("Actual vs Predicted")
            residuals = y_test - y_pred
            axes[1].hist(residuals, bins=40, color="#4A90D9", edgecolor="white", alpha=0.8)
            axes[1].axvline(0, color="red", linestyle="--")
            axes[1].set_xlabel("Residual"); axes[1].set_ylabel("Count"); axes[1].set_title("Residual Distribution")
            sorted_idx = np.argsort(np.abs(model.coef_))
            axes[2].barh([feats[j] for j in sorted_idx], [model.coef_[j] for j in sorted_idx], color="#4A90D9")
            axes[2].set_xlabel("Coefficient"); axes[2].set_title("Feature Importance")
            fig.suptitle(f"Catering Revenue per Booking Party (baseline) — R² = {metrics['r2']:.3f}, RMSE = {metrics['rmse']:.0f}",
                         fontsize=14, fontweight="bold")
            plt.tight_layout()
            plots_rows.append({
                "plot_id": _plot_id(), "run_id": rid,
                "plot_name": "regression_baseline",
                "plot_type": "multi_panel", "plot_data": _fig_to_b64(fig),
                "created_at": _ts(it["day"], 32),
            })
            plt.close(fig)

        print(f"  run {i+1}/{len(REGRESSION_ITERS)}: features={len(feats)}, R²={metrics['r2']:.4f}")


# ---------------------------------------------------------------------------
# Classification iterations
# ---------------------------------------------------------------------------

def _cls_base_query():
    return """
        SELECT mo_d.booking_id, mo_d.trip_day, mo_d.meal_type,
               mo_d.item_id AS dessert_id,
               b.passengers, b.return_date - b.departure_date AS trip_length,
               p.base_multiplier
        FROM meal_orders mo_d
        JOIN menu_items mi_d ON mo_d.item_id = mi_d.item_id
        JOIN bookings b ON mo_d.booking_id = b.booking_id
        JOIN routes r ON b.route_id = r.route_id
        JOIN planets p ON r.destination_id = p.planet_id
        WHERE mi_d.category = 'dessert'
    """


CLASSIFICATION_ITERS = [
    {"features": ["passengers", "trip_length", "base_multiplier"],
     "enriched": False, "n_est": 20, "depth": 2,
     "tag": "baseline – 3 raw features", "day": 1},
]


def seed_classification(con):
    print("\n--- Classification: Dessert Prediction (1 baseline run) ---")

    df_base = con.execute(_cls_base_query()).fetchdf()

    eid = _exp_id()
    experiments_rows.append({
        "experiment_id": eid, "experiment_name": "dessert_prediction",
        "description": "Predict which dessert a customer orders",
        "created_at": _ts(1, 60),
    })

    for i, it in enumerate(CLASSIFICATION_ITERS):
        feats = it["features"]
        X = df_base[feats].values.astype(float)
        y = df_base["dessert_id"].values.astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)

        model = RandomForestClassifier(
            n_estimators=it["n_est"], max_depth=it["depth"], random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "f1_weighted": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "train_size": int(len(X_train)), "test_size": int(len(X_test)),
        }
        params = {"model_type": "RandomForestClassifier", "n_estimators": it["n_est"],
                   "max_depth": it["depth"], "features": feats,
                   "enriched": it["enriched"], "random_state": 42}

        rid = _run_id(); rn = _run_number(eid); mv = _model_ver("dessert_predictor")
        is_last = i == len(CLASSIFICATION_ITERS) - 1

        runs_rows.append({
            "run_id": rid, "experiment_id": eid, "run_number": rn,
            "dag_id": "space_dessert_classification", "task_id": "train",
            "run_ts": _ts(it["day"], 90), "status": "COMPLETED",
            "hyperparameters": json.dumps(params), "metrics": json.dumps(metrics),
            "tags": json.dumps({"iteration": it["tag"], "enriched": it["enriched"]}),
        })
        models_rows.append({
            "model_name": "dessert_predictor", "model_version": mv,
            "run_id": rid, "model_type": "RandomForestClassifier",
            "model_blob": base64.b64encode(pickle.dumps(model)).decode(),
            "stage": "production" if is_last else ("staging" if i == len(CLASSIFICATION_ITERS) - 2 else "archived"),
            "registered_at": _ts(it["day"], 91),
        })

        if i == 0 or is_last:
            classes = sorted(set(y_test) | set(y_pred))
            class_labels = [DESSERT_NAMES.get(c, str(c)) for c in classes]
            cm = confusion_matrix(y_test, y_pred, labels=classes)

            fig, axes = plt.subplots(1, 3, figsize=(18, 5))
            axes[0].imshow(cm, cmap="Blues")
            axes[0].set_xticks(range(len(classes))); axes[0].set_yticks(range(len(classes)))
            axes[0].set_xticklabels(class_labels, rotation=45, ha="right", fontsize=8)
            axes[0].set_yticklabels(class_labels, fontsize=8)
            axes[0].set_xlabel("Predicted"); axes[0].set_ylabel("Actual"); axes[0].set_title("Confusion Matrix")
            for r in range(len(classes)):
                for c in range(len(classes)):
                    axes[0].text(c, r, str(cm[r, c]), ha="center", va="center",
                                 color="white" if cm[r, c] > cm.max() / 2 else "black",
                                 fontsize=9, fontweight="bold")

            sorted_idx = np.argsort(model.feature_importances_)[-12:]
            axes[1].barh([feats[j] for j in sorted_idx],
                         [model.feature_importances_[j] for j in sorted_idx], color="#E8744F")
            axes[1].set_xlabel("Importance"); axes[1].set_title("Top Features")

            x = np.arange(len(classes))
            axes[2].bar(x - 0.15, [list(y_test).count(c) for c in classes], 0.3, label="Actual", color="#4A90D9")
            axes[2].bar(x + 0.15, [list(y_pred).count(c) for c in classes], 0.3, label="Predicted", color="#E8744F")
            axes[2].set_xticks(x); axes[2].set_xticklabels(class_labels, rotation=45, ha="right", fontsize=8)
            axes[2].set_ylabel("Count"); axes[2].set_title("Dessert Distribution"); axes[2].legend()

            fig.suptitle(f"Dessert Prediction (baseline) — Acc = {metrics['accuracy']:.3f}, F1 = {metrics['f1_weighted']:.3f}",
                         fontsize=14, fontweight="bold")
            plt.tight_layout()
            plots_rows.append({
                "plot_id": _plot_id(), "run_id": rid,
                "plot_name": "classification_baseline",
                "plot_type": "multi_panel", "plot_data": _fig_to_b64(fig),
                "created_at": _ts(it["day"], 92),
            })
            plt.close(fig)

        print(f"  run {i+1}/{len(CLASSIFICATION_ITERS)}: features={len(feats)}, "
              f"accuracy={metrics['accuracy']:.4f}, F1={metrics['f1_weighted']:.4f}")


# ---------------------------------------------------------------------------
# Clustering iterations
# ---------------------------------------------------------------------------

def _clust_base_query():
    return """
        SELECT b.customer_id, count(*) AS total_orders,
               avg(mi.price_usd) AS avg_price,
               sum(mi.price_usd * mo.quantity) AS total_spend,
               max(b.passengers) AS passengers,
               count(DISTINCT (mo.trip_day, mo.meal_type)) AS n_meals
        FROM meal_orders mo
        JOIN menu_items mi ON mo.item_id = mi.item_id
        JOIN bookings b ON mo.booking_id = b.booking_id
        GROUP BY b.customer_id HAVING count(*) >= 5
    """


CLUSTERING_ITERS = [
    {"features": ["total_orders", "avg_price", "total_spend"],
     "enriched": False, "k": 3, "tag": "baseline – k=3", "day": 2},
]


def seed_clustering(con):
    print("\n--- Clustering: Culinary Personas (1 baseline run) ---")

    df_base = con.execute(_clust_base_query()).fetchdf()

    eid = _exp_id()
    experiments_rows.append({
        "experiment_id": eid, "experiment_name": "culinary_personas",
        "description": "Segment customers by dining behavior",
        "created_at": _ts(2, 120),
    })

    COLORS = [
        "#4A90D9", "#E8744F", "#50C878", "#9B59B6", "#F5C242",
        "#E74C8B", "#45B7AA", "#FF8C42", "#7C8DB5", "#A3D977",
    ]

    for i, it in enumerate(CLUSTERING_ITERS):
        feats = it["features"]
        k = it["k"]
        X = df_base[feats].values.astype(float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = model.fit_predict(X_scaled)
        sil = float(silhouette_score(X_scaled, labels))

        cluster_profiles = {}
        for c in range(k):
            mask = labels == c
            profile = {"size": int(mask.sum())}
            for col in feats:
                profile[f"avg_{col}"] = float(df_base.loc[mask, col].mean())
            cluster_profiles[f"cluster_{c}"] = profile

        metrics = {
            "silhouette_score": sil, "inertia": float(model.inertia_),
            "n_clusters": k, "n_customers": int(len(df_base)),
            **{f"cluster_{c}_size": int((labels == c).sum()) for c in range(k)},
        }
        params = {"model_type": "KMeans", "n_clusters": k, "features": feats,
                   "scaling": "StandardScaler", "enriched": it["enriched"], "random_state": 42}

        rid = _run_id(); rn = _run_number(eid); mv = _model_ver("persona_model")
        is_last = i == len(CLUSTERING_ITERS) - 1

        runs_rows.append({
            "run_id": rid, "experiment_id": eid, "run_number": rn,
            "dag_id": "food_preference_clustering", "task_id": "train",
            "run_ts": _ts(it["day"], 150), "status": "COMPLETED",
            "hyperparameters": json.dumps(params), "metrics": json.dumps(metrics),
            "tags": json.dumps({"iteration": it["tag"], "enriched": it["enriched"]}),
        })
        models_rows.append({
            "model_name": "persona_model", "model_version": mv,
            "run_id": rid, "model_type": "KMeans+StandardScaler",
            "model_blob": base64.b64encode(pickle.dumps({"kmeans": model, "scaler": scaler})).decode(),
            "stage": "production" if is_last else ("staging" if i == len(CLUSTERING_ITERS) - 2 else "archived"),
            "registered_at": _ts(it["day"], 151),
        })

        if i == 0 or is_last:
            names = [f"Cluster {c}" for c in range(k)]
            fig, axes = plt.subplots(1, 3, figsize=(18, 5))

            scatter_x = df_base["total_spend"] / df_base["n_meals"].clip(lower=1)
            scatter_y = df_base["total_spend"] / df_base["passengers"].clip(lower=1)
            for c in range(k):
                mask = labels == c
                axes[0].scatter(scatter_x[mask], scatter_y[mask],
                                c=COLORS[c % len(COLORS)], label=names[c], alpha=0.6, s=30)
            axes[0].set_xlabel("Avg Meal Spend")
            axes[0].set_ylabel("Spend Per Passenger")
            axes[0].set_title("Customer Personas"); axes[0].legend(fontsize=8)

            pm = [f"avg_{c}" for c in feats]
            label_map = {
                "avg_child_ratio": "Child Ratio",
                "avg_is_all_inclusive": "All Inclusive",
                "avg_is_budget_plan": "Budget Plan",
                "avg_is_high_orbit": "High Orbit",
                "avg_is_low_orbit": "Low Orbit",
            }
            short = {
                f"avg_{c}": label_map.get(f"avg_{c}", c.replace("_", " ").title())
                for c in feats
            }

            if pm:
                x = np.arange(len(pm)); w = 0.8 / k
                for c in range(k):
                    vals = [cluster_profiles[f"cluster_{c}"].get(p, 0) for p in pm]
                    maxv = [max(cluster_profiles[f"cluster_{ci}"].get(p, 1) for ci in range(k)) for p in pm]
                    norm = [v / mv if mv > 0 else 0 for v, mv in zip(vals, maxv)]
                    axes[1].bar(x + c * w, norm, w, label=names[c], color=COLORS[c % len(COLORS)])
                axes[1].set_xticks(x + w * (k - 1) / 2)
                axes[1].set_xticklabels([short.get(p, p) for p in pm], fontsize=8, rotation=45, ha="right")
                axes[1].set_ylabel("Normalized"); axes[1].set_title("Profiles"); axes[1].legend(fontsize=8)

            sizes = [cluster_profiles[f"cluster_{c}"]["size"] for c in range(k)]
            axes[2].pie(sizes, labels=names, colors=COLORS[:k],
                        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 10})
            axes[2].set_title("Distribution")

            fig.suptitle(f"Culinary Personas (baseline, k={k}) — Silhouette = {sil:.3f}",
                         fontsize=14, fontweight="bold")
            plt.tight_layout()
            plots_rows.append({
                "plot_id": _plot_id(), "run_id": rid,
                "plot_name": "clustering_baseline",
                "plot_type": "multi_panel", "plot_data": _fig_to_b64(fig),
                "created_at": _ts(it["day"], 152),
            })
            plt.close(fig)

        print(f"  run {i+1}/{len(CLUSTERING_ITERS)}: features={len(feats)}, k={k}, silhouette={sil:.4f}")


# ---------------------------------------------------------------------------

def main():
    os.makedirs(SEED_DIR, exist_ok=True)

    tmp_db = os.path.join(SEED_DIR, "_tmp_seed.duckdb")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    con = duckdb.connect(tmp_db)

    print("=== Building temporary DB with training data ===")
    run_sql_file(con, "schema.sql")
    run_sql_file(con, "ml_schema.sql")
    run_sql_file(con, "fixtures.sql")
    run_sql_file(con, "generate_ml_data.sql")
    run_sql_file(con, "generate_food_data.sql")

    print("\n=== Training baseline models & generating seed data ===")
    seed_regression(con)
    seed_classification(con)
    seed_clustering(con)

    con.close()
    os.remove(tmp_db)

    pd.DataFrame(experiments_rows).to_csv(os.path.join(SEED_DIR, "ml_experiments.csv"), index=False)
    pd.DataFrame(runs_rows).to_csv(os.path.join(SEED_DIR, "ml_runs.csv"), index=False)
    pd.DataFrame(models_rows).to_csv(os.path.join(SEED_DIR, "ml_models.csv"), index=False)
    pd.DataFrame(plots_rows).to_csv(os.path.join(SEED_DIR, "ml_plots.csv"), index=False)

    print(f"\n=== Seed CSVs written to {SEED_DIR} ===")
    print(f"  ml_experiments.csv  ({len(experiments_rows)} rows)")
    print(f"  ml_runs.csv         ({len(runs_rows)} rows)")
    print(f"  ml_models.csv       ({len(models_rows)} rows)")
    print(f"  ml_plots.csv        ({len(plots_rows)} rows)")


if __name__ == "__main__":
    main()
