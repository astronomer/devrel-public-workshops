import polars as pl

_SPACE_FOOD_PREMIUM = 4

FEATURE_COLUMNS = [
    "booking_id",
    "passengers",
    "trip_length_days",
    "destination_planet",
    "dest_base_multiplier",
    "route_base_fare_usd",
    "fare_per_person_per_day",
    "home_planet",
    "home_base_multiplier",
    "is_traveling_to_home_planet",
    "cosmarket_order_count",
    "cosmarket_avg_item_price",
    "cosmarket_total_home_spend",
    "cosmarket_dessert_share",
    "cosmarket_avg_spice_level",
    "cosmarket_veg_share",
]


def build_frames(history: dict) -> dict:
    frames = {name: pl.DataFrame(records) for name, records in history.items()}
    b = frames["bookings"]

    casts = []
    if "departure_date" in b.columns and b.schema["departure_date"] == pl.String:
        casts.append(pl.col("departure_date").str.to_date())
    if "return_date" in b.columns and b.schema["return_date"] == pl.String:
        casts.append(pl.col("return_date").str.to_date())
    if "booked_at" in b.columns and b.schema["booked_at"] == pl.String:
        casts.append(pl.col("booked_at").str.to_datetime())
    if "promo_code" in b.columns:
        casts.append(pl.col("promo_code").cast(pl.String))
    if casts:
        b = b.with_columns(casts)

    if "trip_length_days" not in b.columns:
        b = b.with_columns(
            (pl.col("return_date") - pl.col("departure_date")).dt.total_days().alias("trip_length_days")
        )

    frames["bookings"] = b
    return frames


def compute_spend_labels(frames: dict) -> pl.DataFrame:
    lines = (
        frames["meal_orders"]
        .join(frames["menu_items"].select("item_id", "price_usd"), on="item_id", how="left")
        .with_columns((pl.col("quantity") * pl.col("price_usd")).alias("line_total"))
    )
    totals = lines.group_by("booking_id").agg(
        pl.col("line_total").sum().alias("total_food_spend")
    )
    trip = frames["bookings"].select(
        "booking_id",
        "passengers",
        (pl.col("return_date") - pl.col("departure_date")).dt.total_days().alias("trip_days"),
    )
    return (
        totals.join(trip, on="booking_id", how="inner")
        .with_columns(
            (_SPACE_FOOD_PREMIUM * pl.col("total_food_spend") / pl.col("trip_days") / pl.col("passengers")).alias(
                "food_spend_pp_pd"
            )
        )
        .select("booking_id", "food_spend_pp_pd")
        .sort("booking_id")
    )


def compute_spend_features(frames: dict) -> pl.DataFrame:
    planets = frames["planets"]
    dest = planets.select(
        pl.col("planet_id").alias("destination_id"),
        pl.col("planet_name").alias("destination_planet"),
        pl.col("base_multiplier").alias("dest_base_multiplier"),
    )
    home = planets.select(
        pl.col("planet_id").alias("home_planet_id"),
        pl.col("planet_name").alias("home_planet"),
        pl.col("base_multiplier").alias("home_base_multiplier"),
    )

    base = (
        frames["bookings"]
        .join(
            frames["routes"].select(
                "route_id",
                "destination_id",
                pl.col("base_fare_usd").alias("route_base_fare_usd"),
            ),
            on="route_id",
            how="left",
        )
        .join(dest, on="destination_id", how="left")
        .join(frames["customers"].select("customer_id", "home_planet_id"), on="customer_id", how="left")
        .join(home, on="home_planet_id", how="left")
        .join(
            frames["payments"].select("booking_id", pl.col("amount_usd").alias("trip_fare_usd")),
            on="booking_id",
            how="left",
        )
    )

    base = base.with_columns(
        (pl.col("home_planet_id") == pl.col("destination_id")).alias("is_traveling_to_home_planet"),
    )
    base = base.with_columns(
        (pl.col("trip_fare_usd") / pl.col("passengers") / pl.col("trip_length_days")).alias(
            "fare_per_person_per_day"
        )
    )

    cm = (
        frames["cosmarket_orders"]
        .join(
            frames["menu_items"].select("item_id", "price_usd", "category", "is_vegetarian", "spice_level"),
            on="item_id",
            how="left",
        )
        .with_columns((pl.col("quantity") * pl.col("price_usd")).alias("line_total"))
    )
    cm_agg = cm.group_by("customer_id").agg(
        pl.len().alias("cosmarket_order_count"),
        pl.col("line_total").sum().alias("cosmarket_total_home_spend"),
        pl.col("quantity").sum().alias("_qty"),
        ((pl.col("category") == "dessert").cast(pl.Int64) * pl.col("quantity")).sum().alias("_dessert_qty"),
        (pl.col("spice_level") * pl.col("quantity")).sum().alias("_spice_qty"),
        (pl.col("is_vegetarian").cast(pl.Int64) * pl.col("quantity")).sum().alias("_veg_qty"),
    )
    cm_agg = cm_agg.with_columns(
        (pl.col("cosmarket_total_home_spend") / pl.col("_qty")).alias("cosmarket_avg_item_price"),
        (pl.col("_dessert_qty") / pl.col("_qty")).alias("cosmarket_dessert_share"),
        (pl.col("_spice_qty") / pl.col("_qty")).alias("cosmarket_avg_spice_level"),
        (pl.col("_veg_qty") / pl.col("_qty")).alias("cosmarket_veg_share"),
    ).select(
        "customer_id",
        "cosmarket_order_count",
        "cosmarket_avg_item_price",
        "cosmarket_total_home_spend",
        "cosmarket_dessert_share",
        "cosmarket_avg_spice_level",
        "cosmarket_veg_share",
    )

    return (
        base.join(cm_agg, on="customer_id", how="left")
        .with_columns(
            pl.col("cosmarket_order_count").fill_null(0),
            pl.col("cosmarket_total_home_spend").fill_null(0.0),
        )
        .select(FEATURE_COLUMNS)
        .sort("booking_id")
    )


def one_hot_encode(df: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    # One-hot encode the listed categorical columns into 0/1 indicator columns
    # (every other column is left as-is) so the model gets an all-numeric matrix.
    df = df.to_dummies(columns=columns)
    bool_cols = [c for c, t in df.schema.items() if t == pl.Boolean]
    return df.with_columns([pl.col(c).cast(pl.Int64) for c in bool_cols]).fill_null(0)
