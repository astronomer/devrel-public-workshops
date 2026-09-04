"""
Integration tests for the AstroTrips conditions API and the helpers built on top of it.

The API is deterministic, so the same planet and date always produce the same reading.
"""

from include.helper_functions import fetch_conditions, map_planets_to_conditions
from include.weather_api import get_planet_weather, get_solar_activity

_PLANETS = [
    {"planet": "Moon", "planet_id": 1001},
    {"planet": "Mars", "planet_id": 1002},
]


def test_planet_weather_is_deterministic():
    first = get_planet_weather(1002, "2026-03-01")
    second = get_planet_weather(1002, "2026-03-01")

    assert first == second
    assert -100 <= first["temperature_c"] <= 200
    assert 0.0 <= first["storm_risk"] <= 1.0
    assert first["visibility"] in ("clear", "hazy", "poor")


def test_solar_activity_is_deterministic():
    first = get_solar_activity(1002, "2026-03-01")
    second = get_solar_activity(1002, "2026-03-01")

    assert first == second
    assert 0.0 <= first["flare_index"] <= 10.0
    assert first["radiation_level"] in ("nominal", "elevated", "severe")


def test_fetch_conditions_returns_one_reading_per_planet_and_day():
    readings = fetch_conditions(_PLANETS, "2026-03-01", [0, 1])

    assert len(readings) == 4
    assert {r["reading_date"] for r in readings} == {"2026-03-01", "2026-03-02"}


def test_map_planets_to_conditions_pivots_into_one_row_per_date():
    readings = fetch_conditions(_PLANETS, "2026-03-01", [0, 1])

    table = map_planets_to_conditions(readings, _PLANETS, "storm_risk")

    assert table["headers"] == ["reading_date", "Moon", "Mars"]
    assert [row[0] for row in table["rows"]] == ["2026-03-01", "2026-03-02"]
    assert all(len(row) == 3 for row in table["rows"])


def test_map_planets_to_conditions_accepts_a_single_destination():
    readings = fetch_conditions(_PLANETS[0], "2026-03-01", [0])

    table = map_planets_to_conditions(readings, _PLANETS[0], "visibility")

    assert table["headers"] == ["reading_date", "Moon"]
    assert len(table["rows"]) == 1
