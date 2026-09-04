"""
# Toy Dag scheduled to run on an update to one asset in each of 2 groups
"""

from airflow.sdk import Asset, dag, task
from pendulum import datetime


@dag(
    start_date=datetime(2024, 11, 1),
    schedule=(
        (Asset("launch-temperature") | Asset("launch-storm-risk"))
        & (Asset("launch-visibility") | Asset("solar-activity"))
    ),  # Runs when one asset in each group is updated
    # Use conditional logic to schedule a Dag based on assets.
    # Use () instead of [] to be able to use conditional asset scheduling!
    doc_md=__doc__,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def conditional_asset_schedule():
    @task
    def say_hello():
        print("Cleared for launch")

    say_hello()


conditional_asset_schedule()