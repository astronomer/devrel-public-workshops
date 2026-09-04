from airflow.sdk import dag, task
from pendulum import datetime

from include.helper_functions import expensive_trajectory_calculation


@dag(
    dag_display_name="Solution: top_level_code",
    start_date=datetime(2026, 6, 1),
    max_active_runs=3,
    schedule=None,
    tags=["solution"],
    default_args={"owner": "Astro", "retries": 3},
)
def top_level_code():

    @task
    def reveal_the_trajectory_correction():
        correction = expensive_trajectory_calculation()
        print(f"The optimal trajectory correction is... {correction} degrees.")

    reveal_the_trajectory_correction()


top_level_code()
