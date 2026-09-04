"""
This Dag shows how to use common Airflow decorators.

- PythonOperator -> @task
- BashOperator -> @task.bash 
- BranchPythonOperator -> @task.branch
- PythonSensor -> @task.sensor

See also:
- Learn guide: https://www.astronomer.io/docs/learn/airflow-decorators
"""

from airflow.sdk import chain, dag, task
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.standard.sensors.python import PythonSensor
from airflow.providers.standard.operators.empty import EmptyOperator


@dag(
    start_date=None,
    schedule=None,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def task_flow_api_dag():

    # PythonOperator and @task

    def _say_hi():
        print("Hi!")

    PythonOperator(
        task_id="python_hi_traditional",
        python_callable=_say_hi,
    )

    @task
    def python_hi_taskflow():
        print("Hi!")

    python_hi_taskflow()

    # BashOperator and @task.bash

    BashOperator(
        task_id="bash_hello_traditional",
        bash_command="echo Hello!",
    )

    @task.bash
    def bash_hello_taskflow():
        return "echo Hello!"

    bash_hello_taskflow()

    # BranchPythonOperator and @task.branch

    def _branching():
        import random

        if random.choice([True, False]):
            return "branch_a_traditional"
        else:
            return "branch_b_traditional"

    b1 = BranchPythonOperator(
        task_id="branching_traditional",
        python_callable=_branching,
    )

    e1 = EmptyOperator(task_id="branch_a_traditional")
    e2 = EmptyOperator(task_id="branch_b_traditional")

    b1 >> [e1, e2]

    @task.branch
    def branching_taskflow():
        import random

        if random.choice([True, False]):
            return "branch_a_taskflow"
        else:
            return "branch_b_taskflow"

    e3 = EmptyOperator(task_id="branch_a_taskflow")
    e4 = EmptyOperator(task_id="branch_b_taskflow")

    chain(branching_taskflow(), [e3, e4])

    # PythonSensor and @task.sensor

    def _wait_for_it():
        import random
        import time

        time.sleep(10)
        if random.choice([True, False]):
            return True
        else:
            return False

    s1 = PythonSensor(
        task_id="sensor_traditional",
        poke_interval=10,
        timeout=3600,
        mode="poke",
        python_callable=_wait_for_it,
    )

    @task.sensor(poke_interval=10, timeout=3600, mode="poke")
    def sensor_taskflow():
        import random
        import time

        time.sleep(10)
        if random.choice([True, False]):
            return True
        else:
            return False

    sensor_taskflow()


task_flow_api_dag()
