import pandas as pd


def trip_context(md):
    """Child-related features."""
    keys = ["booking_id", "trip_day", "meal_type"]
    agg = md.groupby(keys).agg(
        passengers=("passengers", "max"),
        trip_length=("trip_length", "max"),
        children=("children", "max"),
    )
    agg["has_children"] = (agg["children"] > 0).astype(int)
    agg["child_ratio"] = agg["children"].astype(float) / agg["passengers"].clip(lower=1)
    agg.drop(columns=["passengers", "trip_length", "children"], inplace=True)
    return agg.reset_index()


def booking_demographics(md):
    """Agent, accommodation, destination meal plan, and loyalty indicators."""
    keys = ["booking_id", "trip_day", "meal_type"]
    first_row = md.groupby(keys).first()

    r = pd.DataFrame(index=first_row.index)
    r["has_promo"] = first_row["promo_code"].notna().astype(int)
    r["is_business"] = (first_row["travel_type"] == "business").astype(int)

    loyalty = first_row["loyalty_tier"]
    r["is_gold"] = (loyalty == "gold").astype(int)
    r["is_silver"] = (loyalty == "silver").astype(int)

    agent = first_row["booking_agent"]
    r["is_gemini"] = (agent == "gemini").astype(int)
    r["is_claude"] = (agent == "claude").astype(int)
    r["is_chatgpt"] = (agent == "chatgpt").astype(int)
    r["is_llama"] = (agent == "llama").astype(int)

    accom = first_row["accommodation_type"]
    r["is_high_orbit"] = (accom == "high_orbit").astype(int)
    r["is_low_orbit"] = (accom == "low_orbit").astype(int)

    plan = first_row["food_plan"]
    r["is_all_inclusive"] = (plan == "all_inclusive").astype(int)
    r["is_budget_plan"] = (plan == "budget").astype(int)
    return r.reset_index()


def compound_scores(trip_df, demo_df):
    """Interaction features combining demographics and trip context."""
    keys = ["booking_id", "trip_day", "meal_type"]
    m = demo_df.merge(trip_df[keys + ["has_children"]], on=keys)

    r = m[keys].copy()
    r["c_gemini_highorbit_allinc_biz"] = (
        m["is_gemini"] + m["is_high_orbit"] + m["is_all_inclusive"] + m["is_business"]
    ) / 4.0
    r["c_chatgpt_gold_kids"] = (
        m["is_chatgpt"] + m["is_gold"] + m["has_children"]
    ) / 3.0
    r["c_llama_loworbit_budget_promo"] = (
        m["is_llama"] + m["is_low_orbit"] + m["is_budget_plan"] + m["has_promo"]
    ) / 4.0
    r["c_claude_highorbit_allinc_nokids"] = (
        m["is_claude"]
        + m["is_high_orbit"]
        + m["is_all_inclusive"]
        + (1 - m["has_children"])
    ) / 4.0
    r["c_llama_loworbit_budget_nogold"] = (
        m["is_llama"]
        + m["is_low_orbit"]
        + m["is_budget_plan"]
        + (1 - m["is_gold"])
    ) / 4.0
    return r
