"""
### Dag that performs basic math operations

This Dag is a simple example of how to use a custom operator to perform basic
math operations.
Demo: dag.test() and Airflow testing
"""

from airflow.sdk import Param, chain, dag, task
from pendulum import datetime

from include.custom_operator import MyBasicMathOperator
from include.helper_functions import calculate_launch_offset


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    doc_md=__doc__,
    params={
        "base_fare_usd": Param(25000, type="integer"),
        "base_multiplier": Param(1.2, type="number"),
    },
    default_args={"retries": 3},
    tags=["syntax_example"],
)
def custom_operator_dag_test():

    @task
    def pick_a_launch_offset(**context) -> int:
        "Return the trajectory offset for the configured route."
        return calculate_launch_offset(
            base_fare_usd=context["params"]["base_fare_usd"],
            multiplier=context["params"]["base_multiplier"],
        )

    pick_a_launch_offset_obj = pick_a_launch_offset()

    operate_with_23 = MyBasicMathOperator(
        task_id="operate_with_23",
        first_number=pick_a_launch_offset_obj,
        second_number=23,
        operation="+",
    )

    chain(
        pick_a_launch_offset_obj,
        operate_with_23,
    )


dag_obj = custom_operator_dag_test()


if __name__ == "__main__":
    # conn_path = "dag_test/connections.yaml"
    # variables_path = "dag_test/variables.yaml"

    # In Airflow 3, dag.test() takes a logical_date, not an execution_date.
    dag_obj.test(
        logical_date=datetime(2026, 6, 1),
        # conn_file_path=conn_path,
        # variable_file_path=variables_path,
        run_conf={"base_fare_usd": 5000, "base_multiplier": 0.8},
    )
