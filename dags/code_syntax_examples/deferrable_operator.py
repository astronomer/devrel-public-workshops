"""
This Dag shows the TriggerDagRunOperator in deferrable mode.

Check to see if deferrable mode is available for a specific operator in
the Astronomer Registry: https://registry.astronomer.io/
"""

from airflow.sdk import dag
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from include.custom_deferrable_operator import MyDeferrableOperator


@dag(
    start_date=None,
    schedule=None,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def deferrable_operator():

    tdro = TriggerDagRunOperator(
        task_id="tdro",
        trigger_dag_id="task_flow_api_dag",
        wait_for_completion=True,
        deferrable=True,
    )

    mdo = MyDeferrableOperator(
        task_id="mdo", wait_for_completion=True, deferrable=True, poke_interval=5
    )


deferrable_operator()
