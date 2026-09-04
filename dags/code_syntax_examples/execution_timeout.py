"""
This Dag shows how to use execution_timeouts
"""

from airflow.sdk import chain, dag, task
from datetime import timedelta
import time


@dag(
    start_date=None,
    schedule=None,
    tags=["syntax_example"],
    default_args={"execution_timeout": timedelta(seconds=10), "retries": 3},
)
def execution_timeout():

    @task
    def quick_task():
        time.sleep(5)
        return "quick"

    @task
    def slow_task():
        time.sleep(15)
        return "slow"

    @task(execution_timeout=timedelta(seconds=20))  # overriding the Dag-level timeout
    def slow_task_that_got_an_extension():
        time.sleep(15)
        return "slow"

    quick_task()
    slow_task()
    slow_task_that_got_an_extension()


execution_timeout()
