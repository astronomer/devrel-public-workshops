"""
Generate the AstroTrips launch readiness report.

This Dag fetches the forecast launch conditions and the archived readings from the two
upstream Dags via XCom and generates a report with the data.

EXERCISE 1: Give the Dag an AssetOrTimeSchedule.
EXERCISE 3: Set the owner and retries for the Dag, and cap the consecutive failed runs.
"""

import logging

from airflow.sdk import (
    Asset,
    AssetOrTimeSchedule,
    CronTriggerTimetable,
    dag,
    task,
)
from pendulum import datetime

from include.helper_functions import pull_from_producer

t_log = logging.getLogger("airflow.task")

_CONDITIONS_DAG_ID = "planet_conditions"
_HISTORY_DAG_ID = "launch_window_history"

_PLANET_CONDITIONS = Asset("planet-conditions")
_LAUNCH_TEMPERATURE = Asset("launch-temperature")
_LAUNCH_STORM_RISK = Asset("launch-storm-risk")
_LAUNCH_VISIBILITY = Asset("launch-visibility")
_SOLAR_ACTIVITY = Asset("solar-activity")


@dag(
    dag_display_name="1./3. Exercise: Launch readiness report 📒",
    start_date=datetime(2026, 6, 1),

    ### EXERCISE 1 ###
    # Schedule the Dag to run every day at midnight UTC
    # AND whenever both "planet-conditions" and "launch-temperature" are updated
    # AS WELL AS ONE OF the assets "launch-storm-risk" OR "launch-visibility".
    #
    # Replace `schedule=None` with an AssetOrTimeSchedule. It takes two arguments, and the
    # Dag runs when EITHER of them fires:
    #
    #     timetable=CronTriggerTimetable("<cron>", timezone="UTC")   <- the time half
    #     assets=(<asset expression>)                                <- the data half
    #
    # Build the asset expression from the _PLANET_CONDITIONS style constants defined ABOVE
    # this decorator, combined with & (both) and | (either one).
    #
    # Watch the precedence: & binds tighter than |, so "a & b & c | d" is read as
    # "(a & b & c) | d". Put the OR group in its own parentheses.
    #
    # AssetOrTimeSchedule and CronTriggerTimetable are already imported at the top of this
    # file. For worked examples see dags/code_syntax_examples/asset_or_time_schedule.py
    # (the outer structure) and conditional_asset_schedule.py (the & and | operators).

    ### START CODE HERE ###
    schedule=None,
    ### END CODE HERE ###

    doc_md=__doc__,
    description="Generate the AstroTrips launch readiness report.",

    ### EXERCISE 3 ###
    # Set the owner of the Dag to your name and the number of retries to 3.

    ### START CODE HERE ###
    ### END CODE HERE ###

    ### EXERCISE 3 ###
    # Make sure this Dag never has more than 6 consecutive failed runs.

    ### START CODE HERE ###
    ### END CODE HERE ###
    tags=["exercise", "exercise_1", "exercise_3"],
)
def launch_readiness_report():

    # Every fetch task declares the asset it reads as an inlet. That gives the task access to
    # the asset's event history, which is how it finds the run that produced the data.
    @task(inlets=[_PLANET_CONDITIONS])
    def fetch_conditions_table(**context) -> dict:
        return pull_from_producer(
            context, _PLANET_CONDITIONS, _CONDITIONS_DAG_ID, "create_conditions_table"
        )

    @task(inlets=[_LAUNCH_TEMPERATURE])
    def fetch_temperature(**context) -> dict:
        return pull_from_producer(
            context, _LAUNCH_TEMPERATURE, _HISTORY_DAG_ID, "get_temperature"
        )

    @task(inlets=[_LAUNCH_STORM_RISK])
    def fetch_storm_risk(**context) -> dict:
        return pull_from_producer(
            context, _LAUNCH_STORM_RISK, _HISTORY_DAG_ID, "get_storm_risk"
        )

    @task(inlets=[_LAUNCH_VISIBILITY])
    def fetch_visibility(**context) -> dict:
        return pull_from_producer(
            context, _LAUNCH_VISIBILITY, _HISTORY_DAG_ID, "get_visibility"
        )

    @task(inlets=[_SOLAR_ACTIVITY])
    def fetch_solar_activity(**context) -> dict:
        return pull_from_producer(
            context, _SOLAR_ACTIVITY, _HISTORY_DAG_ID, "get_solar_activity"
        )

    # get_id_for_one_planet does not produce an asset of its own, but it runs in the same
    # launch_window_history run as get_temperature, so the launch-temperature event carries
    # the run id needed to reach its XCom.
    @task(inlets=[_LAUNCH_TEMPERATURE])
    def fetch_planet(**context) -> dict:
        return pull_from_producer(
            context, _LAUNCH_TEMPERATURE, _HISTORY_DAG_ID, "get_id_for_one_planet"
        )

    @task
    def generate_report(
        conditions_table: dict,
        temperature: dict,
        storm_risk: dict,
        visibility: dict,
        solar_activity: dict,
        planet: dict,
    ):
        from tabulate import tabulate

        if conditions_table:
            t_log.info("Forecast launch conditions:")
            t_log.info(
                tabulate(
                    conditions_table["rows"],
                    headers=conditions_table["headers"],
                    tablefmt="grid",
                ),
            )

        if temperature:
            my_planet = planet["planet"]
            reading_date = temperature["reading_date"]

            t_log.info("--------------------------")
            t_log.info(f"Archived launch conditions for {my_planet} on {reading_date}:")
            t_log.info(f"Surface temperature: {temperature['value']} C")
        if storm_risk:
            t_log.info(f"Storm risk: {storm_risk['value']}")
        if visibility:
            t_log.info(f"Landing site visibility: {visibility['value']}")
        t_log.info("--------------------------")
        if solar_activity:
            t_log.info(f"Solar activity data: {solar_activity}")

    generate_report(
        fetch_conditions_table(),
        fetch_temperature(),
        fetch_storm_risk(),
        fetch_visibility(),
        fetch_solar_activity(),
        fetch_planet(),
    )


launch_readiness_report()
