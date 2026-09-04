"""
Retrieve launch conditions for a list of planets.

This Dag looks up the planet id for every planet provided in a Dag param and uses
it to read launch conditions from the AstroTrips conditions API.
"""

import logging

from airflow.sdk import Asset, Param, chain, dag, task
from pendulum import datetime, duration

from include.helper_functions import fetch_conditions

t_log = logging.getLogger("airflow.task")


@dag(
    dag_display_name="Solution: Planet conditions 🌤️",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    max_consecutive_failed_dag_runs=10,
    doc_md=__doc__,
    description="Retrieve launch conditions for a list of planets.",
    default_args={
        "owner": "Astro",
        "retries": 3,
        "retry_delay": duration(minutes=1),
        "retry_exponential_backoff": True,
    },
    params={
        "my_planets": Param(
            ["Moon", "Mars", "Europa"],
            type="array",
            title="Planets of interest:",
            description="Enter the planets you want launch conditions for. One planet per line.",
        ),
        "measurement": Param(
            "storm_risk",
            type="string",
            enum=["temperature_c", "storm_risk", "visibility"],
            title="Measurement:",
            description="The measurement to put into the conditions table.",
        ),
        "timeframe": Param(
            "today",
            type="string",
            enum=["today", "yesterday", "today_and_tomorrow"],
            title="Forecast vs. archived data",
            description="Choose whether you want conditions for yesterday, today, or today and tomorrow.",
        ),
        "simulate_api_failure": Param(
            False,
            type="boolean",
            title="Simulate API failure",
            description="Set to true to simulate an API failure in the get_id_for_one_planet task.",
        ),
        "simulate_task_delay": Param(
            0,
            type="number",
            title="Simulate task delay",
            description="Set the number of seconds to delay the create_conditions_table task of this Dag.",
        ),
    },
    tags=["solution"],
)
def planet_conditions():

    @task
    def get_planets(**context) -> list:
        return context["params"]["my_planets"]

    planets = get_planets()

    @task
    def get_id_for_one_planet(planet: str, **context) -> dict:
        """Looks up the AstroTrips planet id for the name of one planet."""
        from include.helper_functions import get_planet

        if context["params"]["simulate_api_failure"]:
            raise Exception("Simulated API failure.")

        record = get_planet(planet)

        t_log.info(f"Planet record for {planet}: id={record['planet_id']}")

        return record

    # One dynamically mapped task instance per planet in the list.
    planet_ids = get_id_for_one_planet.expand(planet=planets)

    @task.branch
    def decide_timeframe(**context):
        if context["params"]["timeframe"] == "yesterday":
            return "get_conditions_yesterday"
        elif context["params"]["timeframe"] == "today":
            return "get_conditions_today"
        elif context["params"]["timeframe"] == "today_and_tomorrow":
            return "get_conditions_today_and_tomorrow"
        else:
            raise ValueError("Invalid timeframe parameter.")

    # A Dag run that was triggered manually or by an asset event has no logical date, so
    # `ds` and `logical_date` are undefined. `dag_run.run_after` is always set, which makes
    # it the safe choice for a Dag that can be started either way.
    def _reference_date(context) -> str:
        return context["dag_run"].run_after.strftime("%Y-%m-%d")

    @task
    def get_conditions_yesterday(planets: list | dict, **context) -> list:
        return fetch_conditions(
            planets=planets,
            reference_date=_reference_date(context),
            day_offsets=[-1],
        )

    @task
    def get_conditions_today(planets: list | dict, **context) -> list:
        return fetch_conditions(
            planets=planets,
            reference_date=_reference_date(context),
            day_offsets=[0],
        )

    @task
    def get_conditions_today_and_tomorrow(planets: list | dict, **context) -> list:
        return fetch_conditions(
            planets=planets,
            reference_date=_reference_date(context),
            day_offsets=[0, 1],
        )

    conditions_yesterday = get_conditions_yesterday(planet_ids)
    conditions_today = get_conditions_today(planet_ids)
    conditions_today_and_tomorrow = get_conditions_today_and_tomorrow(planet_ids)

    @task(
        trigger_rule="none_failed",
    )
    def get_conditions_from_response(
        conditions_yesterday: list,
        conditions_today: list,
        conditions_today_and_tomorrow: list,
    ):
        if conditions_yesterday:
            return conditions_yesterday
        elif conditions_today:
            return conditions_today
        elif conditions_today_and_tomorrow:
            return conditions_today_and_tomorrow
        else:
            raise ValueError("No launch conditions found.")

    @task(outlets=[Asset("planet-conditions")])
    def create_conditions_table(conditions: list, planets: list | dict, **context):
        """
        Saves a table of the launch conditions for the planets of interest to the logs.

        Args:
            conditions: The readings for the planets of interest.
            planets: The planet records of the planets of interest.
        """
        import time

        from tabulate import tabulate

        from include.helper_functions import map_planets_to_conditions

        time.sleep(context["params"]["simulate_task_delay"])

        measurement = context["params"]["measurement"]
        conditions_table = map_planets_to_conditions(conditions, planets, measurement)

        t_log.info(f"Launch conditions ({measurement}):")
        t_log.info(
            tabulate(
                conditions_table["rows"],
                headers=conditions_table["headers"],
                tablefmt="grid",
            )
        )

        return conditions_table

    conditions = get_conditions_from_response(
        conditions_today=conditions_today,
        conditions_today_and_tomorrow=conditions_today_and_tomorrow,
        conditions_yesterday=conditions_yesterday,
    )

    create_conditions_table(conditions=conditions, planets=planet_ids)

    chain(
        planet_ids,
        decide_timeframe(),
        [
            conditions_yesterday,
            conditions_today,
            conditions_today_and_tomorrow,
        ],
    )


planet_conditions()
