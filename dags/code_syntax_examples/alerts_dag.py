"""
This Dag shows Dag-level and task-level callbacks.

Note: the SLA feature and its ``sla_miss_callback`` were removed in Airflow 3.
"""

from airflow.sdk import BaseNotifier, dag, task
from pendulum import duration

class MyNotifier(BaseNotifier):
    """
    Basic notifier, says hi.
    """

    def __init__(self):
        pass

    def notify(self, context):
        t_id = context["ti"].task_id
        t_state = context["ti"].state
        print(f"Hi from MyNotifier! {t_id} finished as: {t_state}")


def my_callback_function(context):
    t_id = context["ti"].task_id
    t_state = context["ti"].state
    print(f"Hi from my_callback_function! {t_id} finished as: {t_state}")


@dag(
    start_date=None,
    schedule=None,
    # Dag level callbacks depend on events happening to the Dag itself
    on_success_callback=[my_callback_function, MyNotifier()],
    on_failure_callback=[my_callback_function, MyNotifier()],
    # callbacks provided in the default_args are given to all tasks in the Dag
    default_args={
        "on_execute_callback": [my_callback_function, MyNotifier()],
        "on_retry_callback": [my_callback_function, MyNotifier()],
        "on_success_callback": [my_callback_function, MyNotifier()],
        "on_failure_callback": [my_callback_function, MyNotifier()],
        "on_skipped_callback": [my_callback_function, MyNotifier()],
        "retries": 3,
        "retry_delay": duration(seconds=5)
    },
    tags=["syntax_example"],
)
def callbacks_overview():
    @task(
        # you can override default_args on the task level
        on_execute_callback=[my_callback_function, MyNotifier()],
        on_retry_callback=[my_callback_function, MyNotifier()],
        on_success_callback=[my_callback_function, MyNotifier()],
        on_failure_callback=[my_callback_function, MyNotifier()],
        on_skipped_callback=[my_callback_function, MyNotifier()],  # only responds to AirflowSkipException
    )
    def task_succeeding_task_level_callback():
        return 10

    @task(
        # you can override default_args on the task level
        on_execute_callback=[my_callback_function, MyNotifier()],
        on_retry_callback=[my_callback_function, MyNotifier()],
        on_success_callback=[my_callback_function, MyNotifier()],
        on_failure_callback=[my_callback_function, MyNotifier()],
        on_skipped_callback=[my_callback_function, MyNotifier()],  # only responds to AirflowSkipException
    )
    def task_failing_task_level_callback():
        return 10 / 0

    @task
    def task_succeeding():
        return 10

    @task
    def task_failing():
        return 10 / 0

    task_succeeding()
    task_failing()
    task_succeeding_task_level_callback()
    task_failing_task_level_callback()


callbacks_overview()

