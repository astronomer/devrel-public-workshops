"""
Syncs AstroTrips report data to an Airflow Variable.

Workaround for Astro deployments where the AstroTrips Dashboard plugin runs on the
API server, which does not share the worker's filesystem. This Dag reads all
report and weather data from DuckDB (on the worker) and writes it as JSON to
an Airflow Variable that the plugin can read from anywhere.

Locally this Dag is optional, the plugin falls back to reading DuckDB directly.

Please do not modify this code during the workshop.
"""

import json
from datetime import datetime

import pendulum
from airflow.models import Variable
from airflow.sdk import dag, task
from duckdb_provider.hooks.duckdb_hook import DuckDBHook

_DUCKDB_CONN_ID = "duckdb_astrotrips"

_REPORT_SQL = """
SELECT
    report_date::VARCHAR AS report_date,
    planet_name,
    total_passengers,
    active_trips,
    completed_trips,
    total_gross_fare_usd,
    total_discounts_usd,
    total_net_fare_usd,
    total_paid_usd
FROM daily_planet_report
ORDER BY report_date ASC
"""

_WEATHER_SQL = """
SELECT
    pl.planet_name,
    pw.reading_date::VARCHAR AS reading_date,
    pw.temperature_c,
    pw.storm_risk,
    pw.visibility
FROM planet_weather pw
JOIN planets pl ON pl.planet_id = pw.planet_id
WHERE (pw.planet_id, pw.reading_date) IN (
    SELECT planet_id, MAX(reading_date)
    FROM planet_weather
    GROUP BY planet_id
)
"""


@dag(
    schedule=None,
    tags=["astrotrips", "plugin"],
    default_args={
        "retries": 3,
        "retry_delay": pendulum.duration(seconds=10),
    },
    doc_md=__doc__,
)
def sync():

    @task
    def sync_to_variable():
        hook = DuckDBHook(duckdb_conn_id=_DUCKDB_CONN_ID)
        conn = hook.get_conn()

        report_rows = [list(r) for r in conn.execute(_REPORT_SQL).fetchall()]

        try:
            weather_rows = [list(r) for r in conn.execute(_WEATHER_SQL).fetchall()]
        except Exception:
            weather_rows = []

        conn.close()

        Variable.set(
            "astrotrips_report_data",
            json.dumps({
                "report": report_rows,
                "weather": weather_rows,
                "synced_at": datetime.utcnow().isoformat(),
            }),
        )

    sync_to_variable()


sync()
