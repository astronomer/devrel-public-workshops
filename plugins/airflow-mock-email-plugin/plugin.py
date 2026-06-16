from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

import duckdb
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from airflow.plugins_manager import AirflowPlugin

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = os.environ.get("AIMLOPS_DB_PATH") or os.path.join(
    os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"),
    "include",
    "astrotrips.duckdb",
)

VARIABLE_PREFIX = "aimlops_"

_ICON_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(
    (BASE_DIR / "assets" / "icon.svg").read_bytes()
).decode("ascii")

app = FastAPI(title="Mock Email Plugin")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")

def _load_variable(table: str) -> list[dict] | None:
    """Return the synced rows for a table from its Airflow Variable, or None."""
    try:
        from airflow.models import Variable

        raw = Variable.get(f"{VARIABLE_PREFIX}{table}")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, list) else None


def _resolve_db() -> str:
    """Return the database URI: MotherDuck for the demo, a local DuckDB file otherwise.

    Airflow connections are not resolvable from the plugin's API-server context
    (get_connection raises AirflowNotFoundException there), so the database
    location comes from the environment instead. The demo deployment sets
    ``MOTHERDUCK_URI`` to a full ``md:`` URI (MotherDuck token included);
    workshop attendees leave it unset and read the local DuckDB file.
    """
    return os.environ.get("MOTHERDUCK_URI") or DB_PATH


def _db_records(table: str) -> list[dict]:
    """Return all rows of a table from DuckDB as column-keyed dicts."""
    database = _resolve_db()
    read_only = not database.startswith("md:")
    conn = duckdb.connect(database, read_only=read_only)
    try:
        cur = conn.execute(f"SELECT * FROM {table}")
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_records(table: str) -> list[dict]:
    """Load a whole table: the synced Variable if present, else DuckDB."""
    rows = _load_variable(table)
    return rows if rows is not None else _db_records(table)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _coerce_json(val):
    """JSON columns arrive as dicts/lists or as JSON text depending on source."""
    if isinstance(val, (dict, list)) or val is None:
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (TypeError, json.JSONDecodeError):
            return val
    return val


def _ts(val) -> str | None:
    """Render a timestamp (datetime from DuckDB or string from a Variable)."""
    return None if val is None else str(val)


def _same_id(a, b) -> bool:
    """Compare ids tolerant of int vs string (thread_id types vary by source)."""
    if a is None or b is None:
        return False
    return str(a) == str(b)


def _turn_key(msg: dict) -> tuple:
    return (msg.get("turn") if msg.get("turn") is not None else 0,
            msg.get("message_id") if msg.get("message_id") is not None else 0)


# ---------------------------------------------------------------------------
# Loaders (pure, synchronous, independently testable)
# ---------------------------------------------------------------------------

def load_summary() -> dict:
    threads = _load_records("email_threads")
    messages = _load_records("email_messages")
    traces = _load_records("decision_traces")
    return {
        "threads": len(threads),
        "messages": len(messages),
        "booked": sum(1 for t in threads if t.get("booked") is True),
        "traces": len(traces),
    }


def load_threads() -> list[dict]:
    threads = _load_records("email_threads")
    messages = _load_records("email_messages")
    customers = {c.get("customer_id"): c for c in _load_records("customers")}

    by_thread: dict = {}
    for m in messages:
        by_thread.setdefault(m.get("thread_id"), []).append(m)

    out = []
    for t in threads:
        tid = t.get("thread_id")
        msgs = sorted(by_thread.get(tid, []), key=_turn_key)
        first_inbound = next((m for m in msgs if m.get("direction") == "inbound"), None)
        last = msgs[-1] if msgs else None
        cust = customers.get(t.get("customer_id"), {})
        out.append({
            "thread_id": tid,
            "subject": t.get("subject"),
            "customer_id": t.get("customer_id"),
            "customer_name": cust.get("full_name"),
            "loyalty_tier": cust.get("loyalty_tier"),
            "from_address": (first_inbound or {}).get("sender"),
            "message_count": len(msgs),
            "has_response": any(m.get("direction") == "outbound" for m in msgs),
            "last_direction": (last or {}).get("direction"),
            "last_at": _ts((last or {}).get("created_at")) or _ts(t.get("updated_at")),
            "booked": t.get("booked"),
            "outcome_spend_usd": t.get("outcome_food_spend_usd"),
            "updated_at": _ts(t.get("updated_at")),
        })

    out.sort(key=lambda r: (r.get("last_at") or "", str(r.get("thread_id") or "")), reverse=True)
    return out


def load_messages(thread_id) -> list[dict]:
    msgs = [m for m in _load_records("email_messages") if _same_id(m.get("thread_id"), thread_id)]
    msgs.sort(key=_turn_key)
    return [{
        "message_id": m.get("message_id"),
        "thread_id": m.get("thread_id"),
        "turn": m.get("turn"),
        "direction": m.get("direction"),
        "sender": m.get("sender"),
        "body": m.get("body"),
        "created_at": _ts(m.get("created_at")),
    } for m in msgs]


def _trace_link(trace: dict) -> tuple:
    """Resolve which (thread_id, turn) an outbound reply trace belongs to.

    The link is read from explicit top-level columns first, then from the
    entity_references JSON. This is the contract for trace_capture / seed data:
    a trace carries the thread_id and the turn of the reply it produced.
    """
    er = _coerce_json(trace.get("entity_references"))
    er = er if isinstance(er, dict) else {}
    thread_id = trace.get("thread_id")
    if thread_id is None:
        thread_id = er.get("thread_id")
    turn = trace.get("turn")
    if turn is None:
        turn = er.get("turn")
    return thread_id, turn, er


def _chunk_text(body) -> str:
    """The readable chunk text, with the <chunk id=...> wrapper stripped if present."""
    if not isinstance(body, str):
        return "" if body is None else str(body)
    import re

    match = re.search(r"<chunk\b[^>]*>\s*(.*?)\s*</chunk>", body, re.DOTALL)
    return match.group(1) if match else body


def _context_units_index() -> dict:
    """chunk_id -> {title, text}, for resolving a trace's context_used to readable pieces."""
    index = {}
    for unit in _load_records("context_units"):
        cid = unit.get("chunk_id")
        if cid is not None:
            index[str(cid)] = {"title": unit.get("title"), "text": _chunk_text(unit.get("body"))}
    return index


def _resolve_context(ref, index: dict) -> dict:
    """Turn a context_used entry (a chunk_id, or a dict) into {chunk_id, title, text}."""
    chunk_id = ref.get("chunk_id") if isinstance(ref, dict) else ref
    info = index.get(str(chunk_id), {})
    return {"chunk_id": chunk_id, "title": info.get("title"), "text": info.get("text")}


def load_thread_traces(thread_id) -> list[dict]:
    units = _context_units_index()
    out = []
    for tr in _load_records("decision_traces"):
        link_tid, turn, er = _trace_link(tr)
        if not _same_id(link_tid, thread_id):
            continue
        out.append({
            "trace_id": tr.get("trace_id"),
            "turn": turn,
            "business_unit": tr.get("business_unit"),
            "opened_at": _ts(tr.get("opened_at")),
            "closed_at": _ts(tr.get("closed_at")),
            "entity_references": er,
            "inputs": _coerce_json(tr.get("inputs")),
            "context_used": [
                _resolve_context(c, units)
                for c in (_coerce_json(tr.get("context_used")) or [])
            ],
            "steps": _coerce_json(tr.get("steps")) or [],
            "outcome": _coerce_json(tr.get("outcome")),
        })
    out.sort(key=lambda r: (r.get("turn") if r.get("turn") is not None else 0))
    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/ui", response_class=FileResponse)
async def serve_ui():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/summary")
async def get_summary():
    return await asyncio.to_thread(load_summary)


@app.get("/api/threads")
async def get_threads():
    return await asyncio.to_thread(load_threads)


@app.get("/api/threads/{thread_id}/messages")
async def get_messages(thread_id: str):
    return await asyncio.to_thread(load_messages, thread_id)


@app.get("/api/threads/{thread_id}/traces")
async def get_thread_traces(thread_id: str):
    return await asyncio.to_thread(load_thread_traces, thread_id)


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

class MockEmailPlugin(AirflowPlugin):
    name = "mock_email_plugin"

    fastapi_apps = [
        {
            "app": app,
            "url_prefix": "/inbox",
            "name": "Mock Email Plugin",
        }
    ]

    external_views = [
        {
            "name": "Inbox",
            "href": "inbox/ui",
            "destination": "nav",
            "category": "browse",
            "url_route": "inbox",
            "icon": _ICON_DATA_URI,
        }
    ]
