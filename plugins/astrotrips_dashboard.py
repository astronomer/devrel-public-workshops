import json
import os
from pathlib import Path

import duckdb
from airflow.models import Variable
from airflow.plugins_manager import AirflowPlugin
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

DB_PATH = os.path.join(
    os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"),
    "include",
    "astrotrips.duckdb",
)
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE = (STATIC_DIR / "astrotrips_dashboard.html").read_text()

_REPORT_SQL = """
SELECT
    report_date::VARCHAR,
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
    pw.reading_date::VARCHAR,
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


def _load_from_variable():
    try:
        return json.loads(Variable.get("astrotrips_report_data"))
    except Exception:
        return None


def _query_duckdb():
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        report = [list(r) for r in conn.execute(_REPORT_SQL).fetchall()]
        try:
            weather = [list(r) for r in conn.execute(_WEATHER_SQL).fetchall()]
        except Exception:
            weather = []
        conn.close()
        return {"report": report, "weather": weather, "synced_at": None}
    except Exception:
        return {"report": [], "weather": [], "synced_at": None}


app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    data = _load_from_variable() or _query_duckdb()
    return HTMLResponse(
        content=TEMPLATE.replace("__REPORT_DATA__", json.dumps(data))
    )


class AstroTripsDashboardPlugin(AirflowPlugin):
    name = "astrotrips_dashboard"

    fastapi_apps = [{
        "app": app,
        "url_prefix": "/astrotrips-dashboard",
        "name": "AstroTrips Dashboard",
    }]
    external_views = [{
        "name": "AstroTrips Dashboard",
        "href": "astrotrips-dashboard/dashboard",
        "destination": "nav",
        "url_route": "astrotrips-dashboard",
    }]
