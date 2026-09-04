"""
### .concat() with traditional operators

"""

from airflow.sdk import dag
from airflow.providers.standard.operators.python import PythonOperator
import time


@dag(
    start_date=None,
    schedule=None,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def xcom_concat_traditional():

    def t1_func():
        return [[1], [2], [3]]

    def t2_func():
        return [[4], [5], [6], [7]]

    def map_me_func(input):
        print(f"Sleeping for {input} seconds!")
        time.sleep(input)
        print("Waking up!")

    t1 = PythonOperator(task_id="t1", python_callable=t1_func)

    t2 = PythonOperator(task_id="t2", python_callable=t2_func)

    map_me = PythonOperator.partial(
        task_id="map_me", python_callable=map_me_func
    ).expand(op_args=t1.output.concat(t2.output))


xcom_concat_traditional()
