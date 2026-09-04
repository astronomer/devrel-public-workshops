"""
Fake weather API for the AstroTrips scenario.

Provides deterministic weather and solar activity data for planets based on planet_id and date.
Using a hash-based seed ensures reproducible results for the same inputs.
"""

import hashlib
import random
from datetime import date
from typing import Any


VISIBILITY_OPTIONS = ["clear", "hazy", "poor"]
RADIATION_LEVELS = ["nominal", "elevated", "severe"]


def get_planet_weather(planet_id: int, reading_date: date | str) -> dict[str, Any]:
    """
    Fake API that returns weather for a planet on a given date.

    Args:
        planet_id: The planet ID to get weather for.
        reading_date: The date to get weather for (date object or ISO string).

    Returns:
        Dictionary with weather data:
        - planet_id: int
        - reading_date: str (ISO format)
        - temperature_c: float (-100 to 200)
        - storm_risk: float (0.0 to 1.0)
        - visibility: str ("clear", "hazy", or "poor")
    """
    if isinstance(reading_date, date):
        date_str = reading_date.isoformat()
    else:
        date_str = str(reading_date)

    seed = int(hashlib.sha256(f"{planet_id}:{date_str}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    return {
        "planet_id": planet_id,
        "reading_date": date_str,
        "temperature_c": round(rng.uniform(-100, 200), 1),
        "storm_risk": round(rng.random(), 2),
        "visibility": rng.choice(VISIBILITY_OPTIONS),
    }


def get_weather_batch(planet_ids: list[int], reading_date: date | str) -> list[dict[str, Any]]:
    """
    Get weather for multiple planets on a single date.

    Args:
        planet_ids: List of planet IDs.
        reading_date: The date to get weather for.

    Returns:
        List of weather dictionaries.
    """
    return [get_planet_weather(pid, reading_date) for pid in planet_ids]


def get_solar_activity(planet_id: int, reading_date: date | str) -> dict[str, Any]:
    """
    Fake API that returns solar activity for a planet on a given date.

    Solar activity is tracked separately from local weather because it affects the whole
    transfer trajectory, not only the landing site.

    Args:
        planet_id: The planet ID to get solar activity for.
        reading_date: The date to get solar activity for (date object or ISO string).

    Returns:
        Dictionary with solar activity data:
        - planet_id: int
        - reading_date: str (ISO format)
        - flare_index: float (0.0 to 10.0)
        - radiation_level: str ("nominal", "elevated", or "severe")
    """
    if isinstance(reading_date, date):
        date_str = reading_date.isoformat()
    else:
        date_str = str(reading_date)

    seed = int(hashlib.sha256(f"solar:{planet_id}:{date_str}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    return {
        "planet_id": planet_id,
        "reading_date": date_str,
        "flare_index": round(rng.uniform(0, 10), 2),
        "radiation_level": rng.choice(RADIATION_LEVELS),
    }


if __name__ == "__main__":
    print("Single planet weather:")
    print(get_planet_weather(1, "2026-06-15"))

    print("\nBatch weather (planets 1-3):")
    for weather in get_weather_batch([1, 2, 3], date(2026, 1, 15)):
        print(weather)

    print("\nSolar activity:")
    print(get_solar_activity(1, "2026-06-15"))
