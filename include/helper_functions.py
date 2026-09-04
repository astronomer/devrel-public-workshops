"""
Helper functions for the AstroTrips flight operations Dags.

These functions run inside tasks, so they never import Airflow context or models.
"""

from datetime import date, timedelta
from time import sleep
from typing import Any

from include.weather_api import get_planet_weather, get_solar_activity

# The AstroTrips destination catalogue. Every destination has an id, which is what the
# conditions API uses to look up readings for it.
PLANETS = {
    "Moon": 1001,
    "Mars": 1002,
    "Europa": 1003,
}


def get_planet(planet: str) -> dict:
    """
    Look up the AstroTrips record for a destination name.

    Args:
        planet: The name of the destination, for example "Mars".

    Returns:
        A destination record with a "planet" and a "planet_id" key.

    Raises:
        ValueError: If the name is not an AstroTrips destination.
    """
    planet_id = PLANETS.get(planet)

    if planet_id is None:
        raise ValueError(f"{planet} is not an AstroTrips destination.")

    return {"planet": planet, "planet_id": planet_id}


def as_planet_list(planets: dict | list[dict] | Any) -> list[dict]:
    """
    Normalise whatever the destination lookup task handed us into a list.

    A single task instance returns one dict. A dynamically mapped task returns a lazy
    sequence of dicts. Both shapes end up here, so the Dag keeps working while you are
    halfway through the dynamic task mapping exercise.
    """
    if isinstance(planets, dict):
        return [planets]
    return list(planets)


def fetch_conditions(
    planets: list[dict] | Any,
    reference_date: str,
    day_offsets: list[int],
) -> list[dict]:
    """
    Read launch conditions for a set of destinations from the AstroTrips conditions API.

    Args:
        planets: Destination records, each with at least a "planet" and a "planet_id" key.
            Accepts the lazy sequence that a dynamically mapped task returns.
        reference_date: The date the offsets are relative to, as an ISO string.
        day_offsets: Offsets in days relative to `reference_date`. `[-1]` is yesterday,
            `[0]` is today, `[0, 1]` is today and tomorrow.

    Returns:
        One reading per destination per requested date.
    """
    base_date = date.fromisoformat(reference_date)

    return [
        get_planet_weather(planet["planet_id"], base_date + timedelta(days=offset))
        for offset in day_offsets
        for planet in as_planet_list(planets)
    ]


def fetch_historic_reading(planet: dict, reading_date: str, measurement: str) -> dict:
    """
    Read a single archived measurement for one destination on one date.

    Args:
        planet: A destination record with a "planet" and a "planet_id" key.
        reading_date: The date to read, as an ISO string.
        measurement: One of "temperature_c", "storm_risk" or "visibility".

    Returns:
        The destination, the date, the measurement name and its value.
    """
    reading = get_planet_weather(planet["planet_id"], reading_date)

    return {
        "planet": planet["planet"],
        "reading_date": reading["reading_date"],
        "measurement": measurement,
        "value": reading[measurement],
    }


def fetch_solar_activity(planet: dict, reading_date: str) -> dict:
    """
    Read archived solar activity for one destination on one date.

    Args:
        planet: A destination record with a "planet" and a "planet_id" key.
        reading_date: The date to read, as an ISO string.

    Returns:
        The destination, the date, the flare index and the radiation level.
    """
    activity = get_solar_activity(planet["planet_id"], reading_date)

    return {"planet": planet["planet"], **activity}


def map_planets_to_conditions(
    readings: list[dict],
    planets: list[dict] | Any,
    measurement: str,
) -> dict:
    """
    Pivot a flat list of readings into one row per date and one column per destination.

    Args:
        readings: Readings as returned by `fetch_conditions`.
        planets: Destination records, each with a "planet" and a "planet_id" key.
        measurement: The measurement to put into the table, for example "storm_risk".

    Returns:
        A dict with a "headers" list and a "rows" list of lists. Headers are kept as an
        explicit list because XCom stores values as JSON, and JSON objects do not
        guarantee key order once they make the round trip through the database.
    """
    planets = as_planet_list(planets)
    name_by_id = {planet["planet_id"]: planet["planet"] for planet in planets}
    headers = ["reading_date"] + list(name_by_id.values())

    by_date: dict[str, dict] = {}
    for reading in readings:
        reading_date = reading["reading_date"]
        row = by_date.setdefault(reading_date, {})
        planet_name = name_by_id.get(reading["planet_id"])
        if planet_name is not None:
            row[planet_name] = reading[measurement]

    rows = [
        [reading_date] + [by_date[reading_date].get(name) for name in name_by_id.values()]
        for reading_date in sorted(by_date)
    ]

    return {"headers": headers, "rows": rows}


def pull_from_producer(context: Any, asset: Any, dag_id: str, task_id: str) -> Any:
    """
    Read the XCom that the task producing `asset` pushed during its most recent run.

    Airflow 3 scopes XComs to a single Dag run, so a cross-Dag pull needs the run id of the
    producing run. The asset event carries that run id, and `inlet_events` exposes the full
    event history for every asset the task declares as an inlet. That works whether this Dag
    run was triggered by an asset update or by its cron schedule.

    Args:
        context: The Airflow task context.
        asset: The asset the producing task updates. Must be declared in the task's inlets.
        dag_id: The Dag that produces the asset.
        task_id: The task that pushes the XCom.

    Returns:
        The XCom value, or None when the asset has never been updated.
    """
    events = context["inlet_events"][asset]

    if not events:
        return None

    return context["ti"].xcom_pull(
        dag_id=dag_id,
        task_ids=task_id,
        run_id=events[-1].source_run_id,
    )


def calculate_launch_offset(base_fare_usd: int, multiplier: float) -> int:
    """
    Deterministic stand-in for a slow trajectory solver.

    Replaces the random number API the original workshop called, so the Dags stay
    reproducible and never depend on an external service.
    """
    return int(round(base_fare_usd * multiplier)) % 100


def expensive_trajectory_calculation() -> int:
    """
    Computes the optimal trajectory correction for the next AstroTrips launch.
    """
    # Imagine this is a very slow solver. You can test it by increasing the sleep time.
    # At some point your Dags will stop parsing correctly!
    sleep(1)
    return 42
