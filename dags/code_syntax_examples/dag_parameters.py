"""
This Dag shows examples for different Dag parameters.

See https://www.astronomer.io/docs/learn/airflow-dag-parameters/ for an extensive list.
"""

from airflow.sdk import Param, dag, task
from pendulum import datetime, duration


@dag(
    dag_id="dag_parameters",  # the Dag id is the unique identifier for the Dag, if not set, the name of the decorated function will be used
    dag_display_name="Dag Parameters 🚀",  # the name displayed in the Airflow UI, can include special characters and emojis
    start_date=datetime(
        2026, 6, 1
    ),  # date after which the Dag can be scheduled, see: https://www.astronomer.io/docs/learn/scheduling-in-airflow/#scheduling-concepts
    schedule="@daily",  # the Dag's schedule, there are many options, see: https://www.astronomer.io/docs/learn/scheduling-in-airflow for options
    catchup=False,  # whether missed runs should be scheduled when the Dag is unpaused. False is the default in Airflow 3, so it is set here only to show the parameter, see: https://www.astronomer.io/docs/learn/rerunning-dags#catchup
    max_active_runs=2,  # maximum number of active Dag runs at any point in time
    max_consecutive_failed_dag_runs=5,  # auto-pauses the Dag after x consecutive failed runs, experimental
    max_active_tasks=10,  # maximum number of active tasks across all runs of this Dag at any point in time
    dagrun_timeout=duration(hours=2),  # timeout duration for runs of this Dag
    fail_fast=True,  # renamed from fail_stop in Airflow 3: fails the whole Dag as soon as any task fails, can only be used with the "all_success" trigger rule
    description="Show several Dag params",  # description of the Dag next to the name in the UI
    doc_md=__doc__,  # add Dag Docs in the UI in markdown, see https://www.astronomer.io/docs/learn/custom-airflow-ui-docs-tutorial
    default_args={
        "owner": "Astro",  # owner of this Dag in the Airflow UI
        "retries": 3,  # tasks retry 3 times before they fail
        "retry_delay": duration(seconds=30),  # tasks wait 30s in between retries
        "retry_exponential_backoff": True,  # wait longer between retries with each attempt
    },
    owner_links={
        "Astro": "https://www.astronomer.io/docs/"
    },  # add links to the owner in the UI
    tags=["syntax_example", "parameters"],  # add tags in the UI
    params={
        "my_string_param": Param(
            "Airflow is awesome!",
            type="string",
            title="Favorite orchestrator:",
            description="Enter your favorite data orchestration tool.",
            section="Important params",
            minLength=1,
            maxLength=200,
        ),
        "my_datetime_param": Param(
            "2026-03-01T00:00:00+00:00",
            type="string",
            format="date-time",
        ),
        "my_enum_param": Param(
            "Mars", type="string", enum=["Moon", "Mars", "Europa"]
        ),
        "my_bool_param": Param(True, type="boolean"),
    },  # Airflow params can add interactive options on manual runs. See: https://www.astronomer.io/docs/learn/airflow-params
)
def dag_parameters():

    @task
    def print_the_params(**context):
        my_string_param = context["params"]["my_string_param"]
        my_datetime_param = context["params"]["my_datetime_param"]
        my_enum_param = context["params"]["my_enum_param"]
        my_bool_param = context["params"]["my_bool_param"]

        print(f"my_string_param: {my_string_param}")
        print(f"my_datetime_param: {my_datetime_param}")
        print(f"my_enum_param: {my_enum_param}")
        print(f"my_bool_param: {my_bool_param}")

    print_the_params()


dag_parameters()
