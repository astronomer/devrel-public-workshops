"""
Visualization helpers for the ML pipeline DAGs.

Each function takes the results dict from the train task plus an
MlopsTracker instance, builds matplotlib figures, logs them via the
tracker, and returns the base64-encoded plot payload for XCom.
"""

from __future__ import annotations

import base64
import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

from include.ml_queries import DESSERT_NAMES

matplotlib.use("Agg")

PERSONA_COLORS = [
    "#4A90D9", "#E8744F", "#50C878", "#9B59B6", "#F5C242",
    "#E74C8B", "#45B7AA", "#FF8C42", "#7C8DB5", "#A3D977",
]


def _finish_figure(fig, tracker, run_id, plot_name, plot_type="multi_panel") -> dict:
    """Log figure to tracker, encode to base64, and return XCom payload."""
    tracker.log_plot(run_id, plot_name, plot_type, fig)
    tracker.end_run(run_id)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plot_b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)

    return {
        "run_id": run_id,
        "plots": [{"name": plot_name, "type": plot_type, "data_b64": plot_b64}],
    }


def plot_regression(results: dict, tracker) -> dict:
    """Actual-vs-predicted scatter, residual histogram, feature coefficients."""
    run_id = results["run_id"]
    y_test = np.array(results["y_test"])
    y_pred = np.array(results["y_pred"])

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    axes[0].scatter(y_test, y_pred, alpha=0.4, s=10, color="#4A90D9")
    lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    axes[0].plot(lims, lims, "r--", linewidth=1)
    axes[0].set_xlabel("Actual Daily Spend (USD)")
    axes[0].set_ylabel("Predicted Daily Spend (USD)")
    axes[0].set_title("Actual vs Predicted")

    residuals = y_test - y_pred
    axes[1].hist(residuals, bins=40, color="#4A90D9", edgecolor="white", alpha=0.8)
    axes[1].axvline(0, color="red", linestyle="--")
    axes[1].set_xlabel("Residual (USD)")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Residual Distribution")

    feature_cols = results["feature_cols"]
    importances = results.get("importances", results.get("coefficients", []))
    importance_label = results.get("importance_label", "Coefficient")
    sorted_idx = np.argsort(np.abs(importances))
    axes[2].barh(
        [feature_cols[i] for i in sorted_idx],
        [importances[i] for i in sorted_idx],
        color="#4A90D9",
    )
    panel_title = "Coefficients" if importance_label == "Coefficient" else "Feature Importance"
    axes[2].set_xlabel(importance_label)
    axes[2].set_title(panel_title)

    model_type = results.get("model_type", "LinearRegression")
    enriched = results["params"].get("enriched", False)
    label = "with features" if enriched else "raw data"
    default_title = (
        f"Catering Revenue per Booking Party \u2014 {model_type} ({label}) \u2014 "
        f"R\u00b2 = {results['metrics']['r2']:.3f}, RMSE = {results['metrics']['rmse']:.0f}"
    )
    fig.suptitle(results.get("plot_title", default_title), fontsize=14, fontweight="bold")
    plt.tight_layout()

    return _finish_figure(fig, tracker, run_id, "regression_overview")


def plot_classification(results: dict, tracker) -> dict:
    """Confusion matrix, top feature importances, dessert distribution."""
    run_id = results["run_id"]
    y_test = np.array(results["y_test"])
    y_pred = np.array(results["y_pred"])

    classes = sorted(set(y_test) | set(y_pred))
    class_labels = [DESSERT_NAMES.get(c, str(c)) for c in classes]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    cm = confusion_matrix(y_test, y_pred, labels=classes)
    axes[0].imshow(cm, cmap="Blues")
    axes[0].set_xticks(range(len(classes)))
    axes[0].set_yticks(range(len(classes)))
    axes[0].set_xticklabels(class_labels, rotation=45, ha="right", fontsize=8)
    axes[0].set_yticklabels(class_labels, fontsize=8)
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")
    axes[0].set_title("Confusion Matrix")
    for i in range(len(classes)):
        for j in range(len(classes)):
            axes[0].text(
                j, i, str(cm[i, j]), ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black",
                fontsize=9, fontweight="bold",
            )

    feature_cols = results["feature_cols"]
    importances = results["feature_importances"]
    sorted_idx = np.argsort(importances)[-15:]
    axes[1].barh(
        [feature_cols[i] for i in sorted_idx],
        [importances[i] for i in sorted_idx],
        color="#E8744F",
    )
    axes[1].set_xlabel("Importance")
    axes[1].set_title("Top Features")

    x = np.arange(len(classes))
    actual_counts = [list(y_test).count(c) for c in classes]
    pred_counts = [list(y_pred).count(c) for c in classes]
    axes[2].bar(x - 0.15, actual_counts, 0.3, label="Actual", color="#4A90D9")
    axes[2].bar(x + 0.15, pred_counts, 0.3, label="Predicted", color="#E8744F")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(class_labels, rotation=45, ha="right", fontsize=8)
    axes[2].set_ylabel("Count")
    axes[2].set_title("Dessert Distribution")
    axes[2].legend()

    enriched = results["params"].get("enriched", False)
    label = "with features" if enriched else "raw data"
    fig.suptitle(
        f"Dessert Prediction ({label}) \u2014 Accuracy = {results['metrics']['accuracy']:.3f}, "
        f"F1 = {results['metrics']['f1_weighted']:.3f}",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()

    return _finish_figure(fig, tracker, run_id, "classification_overview")


def plot_clustering(results: dict, tracker) -> dict:
    """Cluster scatter, normalised persona profiles, size pie chart."""
    run_id = results["run_id"]
    labels = np.array(results["labels"])
    n_clusters = results["n_clusters"]
    profiles = results["cluster_profiles"]
    enriched = results["params"].get("enriched", False)

    persona_names = [f"Cluster {c}" for c in range(n_clusters)]

    plot_data = results["df_for_plot"]
    col_names = list(plot_data.keys())

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    x_col = col_names[0] if len(col_names) > 0 else None
    y_col = col_names[1] if len(col_names) > 1 else None

    if x_col and y_col:
        x_vals = np.array(plot_data[x_col])
        y_vals = np.array(plot_data[y_col])
        for c in range(n_clusters):
            mask = labels == c
            axes[0].scatter(
                x_vals[mask], y_vals[mask],
                c=PERSONA_COLORS[c % len(PERSONA_COLORS)],
                label=persona_names[c], alpha=0.6, s=30,
            )
        axes[0].set_xlabel(x_col.replace("_", " ").title())
        axes[0].set_ylabel(y_col.replace("_", " ").title())
        axes[0].set_title("Customer Personas")
        axes[0].legend(fontsize=8)

    feature_cols = results.get("feature_cols", col_names)
    profile_keys = [f"avg_{c}" for c in feature_cols]
    label_map = {
        "avg_child_ratio": "Child Ratio",
        "avg_is_all_inclusive": "All Inclusive",
        "avg_is_budget_plan": "Budget Plan",
        "avg_is_high_orbit": "High Orbit",
        "avg_is_low_orbit": "Low Orbit",
    }
    display_labels = [
        label_map.get(k, c.replace("_", " ").title())
        for k, c in zip(profile_keys, feature_cols)
    ]

    available_keys = [k for k in profile_keys if k in profiles.get("cluster_0", {})]
    available_labels = [display_labels[i] for i, k in enumerate(profile_keys) if k in profiles.get("cluster_0", {})]

    if available_keys:
        x = np.arange(len(available_keys))
        w = 0.8 / n_clusters
        for c in range(n_clusters):
            vals = [profiles[f"cluster_{c}"].get(k, 0) for k in available_keys]
            max_vals = [max(profiles[f"cluster_{ci}"].get(k, 1) for ci in range(n_clusters)) for k in available_keys]
            norm = [v / mv if mv > 0 else 0 for v, mv in zip(vals, max_vals)]
            axes[1].bar(x + c * w, norm, w, label=persona_names[c],
                        color=PERSONA_COLORS[c % len(PERSONA_COLORS)])
        axes[1].set_xticks(x + w * (n_clusters - 1) / 2)
        axes[1].set_xticklabels(available_labels, fontsize=8, rotation=45, ha="right")
        axes[1].set_ylabel("Normalized")
        axes[1].set_title("Persona Profiles")
        axes[1].legend(fontsize=8)

    sizes = [profiles[f"cluster_{c}"]["size"] for c in range(n_clusters)]
    axes[2].pie(
        sizes, labels=persona_names,
        colors=PERSONA_COLORS[:n_clusters],
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 10},
    )
    axes[2].set_title("Persona Distribution")

    label = "with features" if enriched else "raw data"
    sil = results["metrics"]["silhouette_score"]
    fig.suptitle(
        f"Culinary Personas ({label}) \u2014 k={n_clusters}, Silhouette = {sil:.3f}",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()

    return _finish_figure(fig, tracker, run_id, "clustering_overview")
