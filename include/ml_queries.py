"""
SQL queries and shared helpers for the ML pipeline DAGs.

This module centralises the data-extraction queries so the DAG files
stay focused on the ML logic (train task) that workshop participants write.
"""

from __future__ import annotations


def features_available(conn) -> bool:
    """Check whether the feature-engineering table exists and has data."""
    try:
        conn.execute("SELECT 1 FROM booking_meal_features LIMIT 1")
        return True
    except Exception:
        return False


DESSERT_NAMES = {
    21: "Ktarian Choc. Puff",
    22: "Blue Jello",
    23: "Bob's Raisin Cookies",
    24: "Seldon's Swirl",
    25: "Sweet Kibble",
}

# ---------------------------------------------------------------------------
# Regression: daily catering revenue
# ---------------------------------------------------------------------------

REGRESSION_BASE_QUERY = """
    SELECT
        mo.booking_id,
        mo.trip_day,
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

REGRESSION_ENRICHED_QUERY = """
    SELECT
        agg.booking_id,
        agg.trip_day,
        agg.daily_spend,
        agg.passengers,
        agg.trip_length,
        agg.base_multiplier,
        bmf.is_business,
        bmf.is_gold,
        bmf.is_silver,
        bmf.has_promo,

        bmf.has_children,
        bmf.child_ratio,
        bmf.is_gemini,
        bmf.is_claude,
        bmf.is_chatgpt,
        bmf.is_llama,
        bmf.is_high_orbit,
        bmf.is_low_orbit,
        bmf.is_all_inclusive,
        bmf.is_budget_plan,
        bmf.c_gemini_highorbit_allinc_biz
    FROM (
        SELECT
            mo.booking_id,
            mo.trip_day,
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
    ) agg
    LEFT JOIN booking_meal_features bmf
        ON agg.booking_id = bmf.booking_id AND agg.trip_day = bmf.trip_day
"""

# ---------------------------------------------------------------------------
# Classification: dessert prediction
# ---------------------------------------------------------------------------

CLASSIFICATION_BASE_QUERY = """
    SELECT
        mo_d.booking_id,
        mo_d.trip_day,
        mo_d.meal_type,
        mo_d.item_id AS dessert_id,
        b.passengers,
        b.return_date - b.departure_date AS trip_length,
        p.base_multiplier
    FROM meal_orders mo_d
    JOIN menu_items mi_d ON mo_d.item_id = mi_d.item_id
    JOIN bookings b ON mo_d.booking_id = b.booking_id
    JOIN routes r ON b.route_id = r.route_id
    JOIN planets p ON r.destination_id = p.planet_id
    WHERE mi_d.category = 'dessert'
"""

CLASSIFICATION_ENRICHED_QUERY = """
    SELECT
        mo_d.booking_id,
        mo_d.trip_day,
        mo_d.meal_type,
        mo_d.item_id AS dessert_id,
        b.passengers,
        b.return_date - b.departure_date AS trip_length,
        p.base_multiplier,

        bmf.has_children,
        bmf.child_ratio,
        bmf.has_promo,
        bmf.is_business,
        bmf.is_gold,
        bmf.is_silver,
        bmf.is_gemini,
        bmf.is_claude,
        bmf.is_chatgpt,
        bmf.is_llama,
        bmf.is_high_orbit,
        bmf.is_low_orbit,
        bmf.is_all_inclusive,
        bmf.is_budget_plan,
        bmf.c_gemini_highorbit_allinc_biz,
        bmf.c_chatgpt_gold_kids,
        bmf.c_llama_loworbit_budget_promo,
        bmf.c_claude_highorbit_allinc_nokids,
        bmf.c_llama_loworbit_budget_nogold
    FROM meal_orders mo_d
    JOIN menu_items mi_d ON mo_d.item_id = mi_d.item_id
    JOIN bookings b ON mo_d.booking_id = b.booking_id
    JOIN routes r ON b.route_id = r.route_id
    JOIN planets p ON r.destination_id = p.planet_id
    LEFT JOIN booking_meal_features bmf
        ON mo_d.booking_id = bmf.booking_id
        AND mo_d.trip_day = bmf.trip_day
        AND mo_d.meal_type = bmf.meal_type
    WHERE mi_d.category = 'dessert'
"""

# ---------------------------------------------------------------------------
# Clustering: culinary personas
# ---------------------------------------------------------------------------

CLUSTERING_BASE_QUERY = """
    SELECT
        b.customer_id,
        count(*) AS total_orders,
        avg(mi.price_usd) AS avg_price,
        sum(mi.price_usd * mo.quantity) AS total_spend,
        max(b.passengers) AS passengers,
        count(DISTINCT (mo.trip_day, mo.meal_type)) AS n_meals
    FROM meal_orders mo
    JOIN menu_items mi ON mo.item_id = mi.item_id
    JOIN bookings b ON mo.booking_id = b.booking_id
    GROUP BY b.customer_id
    HAVING count(*) >= 5
"""

CLUSTERING_ENRICHED_QUERY = """
    SELECT
        base.customer_id,
        base.total_orders,
        base.avg_price,
        base.total_spend,
        base.passengers,
        base.n_meals,
        avg(bmf.child_ratio) AS avg_child_ratio,
        avg(bmf.is_all_inclusive) AS avg_is_all_inclusive,
        avg(bmf.is_budget_plan) AS avg_is_budget_plan,
        avg(bmf.is_high_orbit) AS avg_is_high_orbit,
        avg(bmf.is_low_orbit) AS avg_is_low_orbit
    FROM (
        SELECT
            b.customer_id,
            b.booking_id,
            count(*) AS total_orders,
            avg(mi.price_usd) AS avg_price,
            sum(mi.price_usd * mo.quantity) AS total_spend,
            max(b.passengers) AS passengers,
            count(DISTINCT (mo.trip_day, mo.meal_type)) AS n_meals
        FROM meal_orders mo
        JOIN menu_items mi ON mo.item_id = mi.item_id
        JOIN bookings b ON mo.booking_id = b.booking_id
        GROUP BY b.customer_id, b.booking_id
        HAVING count(*) >= 5
    ) base
    JOIN booking_meal_features bmf
        ON base.booking_id = bmf.booking_id
    GROUP BY base.customer_id, base.total_orders, base.avg_price, base.total_spend,
             base.passengers, base.n_meals
"""
