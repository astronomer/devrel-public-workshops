"""
# Toy Dag scheduled to run on a cron schedule and an update to any of 2 upstream assets
"""

from airflow.sdk import Asset, AssetOrTimeSchedule, CronTriggerTimetable, dag, task
from pendulum import datetime


@dag(
    start_date=datetime(2024, 3, 1),
    schedule=AssetOrTimeSchedule(
        timetable=CronTriggerTimetable("0 * * * *", timezone="UTC"),
        assets=(Asset("launch-visibility") | Asset("solar-activity")),
    ),  # Runs every hour and when either of the assets are updated
    # Schedule a Dag both on time and on conditional assets.
    # Use () instead of [] to be able to use conditional asset scheduling!
    doc_md=__doc__,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def asset_or_time_schedule():
    @task
    def say_hello():
        print("Cleared for launch")

    say_hello()


asset_or_time_schedule()
