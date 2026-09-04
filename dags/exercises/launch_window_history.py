"""
Get archived launch conditions for a single planet on a specific launch date.

Mission control uses this Dag to check what the conditions looked like on the day a launch
window opens, so the readiness report can compare the forecast against the archive.

EXERCISE 1: Turn the get_storm_risk task into a producer for the Asset("launch-storm-risk")
            and the get_visibility task into a producer for the Asset("launch-visibility").
"""

import logging

from airflow.sdk import Asset, Param, chain_linear, dag, task
from pendulum import datetime, duration

from include.helper_functions import fetch_historic_reading, fetch_solar_activity

t_log = logging.getLogger("airflow.task")

_TEMPERATURE_TASK_ID = "get_temperature"
_STORM_RISK_TASK_ID = "get_storm_risk"
_VISIBILITY_TASK_ID = "get_visibility"
_SOLAR_ACTIVITY_TASK_ID = "get_solar_activity"


@dag(
    dag_display_name="1. Exercise: Launch window history 🌦️",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    max_consecutive_failed_dag_runs=10,
    doc_md=__doc__,
    default_args={
        "owner": "Astro",
        "retries": 3,
        "retry_delay": duration(minutes=1),
        "retry_exponential_backoff": True,
    },
    params={
        "my_planet": Param(
            "Mars",
            type="string",
            title="Planet of interest:",
            description="Enter the planet you want archived launch conditions for.",
        ),
        "my_launch_date": Param(
            "2026-03-01T00:00:00+00:00",
            type="string",
            format="date-time",
            title="Launch date:",
            description="The day the launch window opens.",
        ),
        "get_temperature": Param(
            True,
            type="boolean",
            title="Get the surface temperature for the launch date",
        ),
        "get_storm_risk": Param(
            True,
            type="boolean",
            title="Get the storm risk for the launch date",
        ),
        "get_visibility": Param(
            True,
            type="boolean",
            title="Get the landing site visibility for the launch date",
            description="Visibility is reported as clear, hazy or poor.",
        ),
        "get_solar_activity": Param(
            True,
            type="boolean",
            title="Get solar activity along the transfer trajectory",
        ),
    },
    tags=["exercise", "exercise_1"],
)
def launch_window_history():

    @task
    def get_id_for_one_planet(**context) -> dict:
        """Looks up the AstroTrips planet id for the planet in the Dag params."""
        from include.helper_functions import get_planet

        planet = context["params"]["my_planet"]
        record = get_planet(planet)

        t_log.info(f"Planet record for {planet}: id={record['planet_id']}")

        return record

    planet = get_id_for_one_planet()

    @task
    def reformat_date(**context) -> str:
        from datetime import datetime

        launch_date = context["params"]["my_launch_date"]
        launch_date = datetime.fromisoformat(launch_date).strftime("%Y-%m-%d")

        return launch_date

    reformatted_date = reformat_date()

    @task.branch
    def determine_data_to_get(**context):
        task_ids_to_run = []

        if context["params"]["get_temperature"]:
            task_ids_to_run.append(_TEMPERATURE_TASK_ID)
        if context["params"]["get_storm_risk"]:
            task_ids_to_run.append(_STORM_RISK_TASK_ID)
        if context["params"]["get_visibility"]:
            task_ids_to_run.append(_VISIBILITY_TASK_ID)
        if context["params"]["get_solar_activity"]:
            task_ids_to_run.append(_SOLAR_ACTIVITY_TASK_ID)

        return task_ids_to_run

    # With the TaskFlow API the function name is the task id, which is what
    # determine_data_to_get branches on.
    @task(outlets=[Asset("launch-temperature")])
    def get_temperature(planet: dict, reading_date: str) -> dict:
        return fetch_historic_reading(
            planet=planet, reading_date=reading_date, measurement="temperature_c"
        )

    ### EXERCISE 1: Turn this task into a producer for the Asset("launch-storm-risk")
    ### START CODE HERE ###
    @task()
    ### END CODE HERE ###
    def get_storm_risk(planet: dict, reading_date: str) -> dict:
        return fetch_historic_reading(
            planet=planet, reading_date=reading_date, measurement="storm_risk"
        )

    ### EXERCISE 1: Turn this task into a producer for the Asset("launch-visibility")
    ### START CODE HERE ###
    @task()
    ### END CODE HERE ###
    def get_visibility(planet: dict, reading_date: str) -> dict:
        return fetch_historic_reading(
            planet=planet, reading_date=reading_date, measurement="visibility"
        )

    @task(outlets=[Asset("solar-activity")])
    def get_solar_activity(planet: dict, reading_date: str) -> dict:
        return fetch_solar_activity(planet=planet, reading_date=reading_date)

    temperature = get_temperature(planet, reformatted_date)
    storm_risk = get_storm_risk(planet, reformatted_date)
    visibility = get_visibility(planet, reformatted_date)
    solar_activity = get_solar_activity(planet, reformatted_date)

    chain_linear(
        [determine_data_to_get(), planet, reformatted_date],
        [temperature, storm_risk, visibility, solar_activity],
    )


launch_window_history()
