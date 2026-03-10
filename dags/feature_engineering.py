"""
Dag creating additional features from booking and customer signup data.
"""

import os
from pathlib import Path
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import dag, task, chain, Asset

_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_PROJECT_ROOT = Path(
    os.environ.get("AIRFLOW_HOME", Path(__file__).resolve().parent.parent)
)
_SQL_DIR = _PROJECT_ROOT / "include" / "sql"


@dag(tags=["features"], schedule=[Asset("db_reload")])
def feature_engineering():

    _start = EmptyOperator(task_id="start")

    @task
    def extract_bookings():
        import duckdb
        import pandas as pd
        from airflow.sdk.bases.hook import BaseHook

        db_path = BaseHook.get_connection(_CONN_ID).host
        conn = duckdb.connect(db_path, read_only=True)
        df = pd.read_sql((_SQL_DIR / "booking_detail.sql").read_text(), conn)
        conn.close()
        return df.to_dict(orient="list")

    @task
    def trip_context(bookings_data):
        import pandas as pd
        from include.feature_helpers import trip_context as _fn

        return _fn(pd.DataFrame(bookings_data)).to_dict(orient="list")

    @task
    def booking_demographics(bookings_data):
        import pandas as pd
        from include.feature_helpers import booking_demographics as _fn

        return _fn(pd.DataFrame(bookings_data)).to_dict(orient="list")


    # Add your tasks here

    _extract_bookings = extract_bookings()
    chain(_start, _extract_bookings)
    _trip_context = trip_context(_extract_bookings)
    _booking_demographics = booking_demographics(_extract_bookings)


feature_engineering()
