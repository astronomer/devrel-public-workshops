"""
This Dag shows how to set task retries at the Dag and task level.

You can also set the following Airflow configurations to control retries at the Airflow environment level:
- AIRFLOW__CORE__DEFAULT_TASK_RETRIES (default is 0)
- AIRFLOW__CORE__DEFAULT_TASK_RETRY_DELAY (default is 300 seconds=5 minutes)
- AIRFLOW__CORE__MAX_TASK_RETRY_DELAY (default is 86400 seconds=24 hours, max for exponential backoff!)


See also:
- Learn guide: https://www.astronomer.io/docs/learn/rerunning-dags/#automatically-retry-tasks
- Airflow configuration reference: https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html
"""

from airflow.sdk import dag, task
from pendulum import datetime, duration
from airflow.providers.standard.operators.bash import BashOperator


@dag(
    start_date=None,
    schedule=None,
    default_args={
        "retries": 3,
        "retry_delay": duration(minutes=1),
        "retry_exponential_backoff": True,
    },  # set defaults for all tasks in the Dag overriding any config-level defaults
    doc_md=__doc__,
    tags=["syntax_example"],
)
def retries_dag():

    @task
    def failing_task_1():
        """
        TaskFlow API task that fails and retries according to the Dag-level defaults.
        """
        raise ValueError("This task will always fail.")

    failing_task_1()

    @task(retries=5, retry_delay=duration(seconds=10), retry_exponential_backoff=False)
    def failing_task_2():
        """
        TaskFlow API task that fails and retries with task-level overrides.
        """
        raise ValueError("This task will always fail.")

    failing_task_2()

    # traditional task that fails and retries according to the Dag-level defaults
    failing_task_3 = BashOperator(
        task_id="failing_task_3",
        bash_command="exit 1",
    )

    # traditional task that fails and retries with task-level overrides
    failing_task_4 = BashOperator(
        task_id="failing_task_4",
        bash_command="exit 1",
        retries=5,
        retry_delay=duration(seconds=10),
        retry_exponential_backoff=False,
    )


retries_dag()
