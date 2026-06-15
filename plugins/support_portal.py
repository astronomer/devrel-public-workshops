import json
import os
from datetime import datetime
from pathlib import Path

import duckdb
from airflow.configuration import conf
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
TEMPLATE = (STATIC_DIR / "dashboard.html").read_text()

STATUS_COLORS = {
    "pending": ("#6b7280", "#f3f4f6"),
    "analyzed": ("#2676FF", "#E4EEFF"),
    "routed": ("#A067FB", "#F0E6FE"),
    "response_drafted": ("#E89428", "#FDF0DC"),
    "approved": ("#19BA5A", "#E2F6EA"),
    "rejected": ("#F03A47", "#FDE9EB"),
}
CATEGORY_COLORS = {
    "safety": "#F03A47",
    "service": "#2676FF",
    "value": "#E89428",
    "experience": "#19BA5A",
}
SENTIMENT_ICONS = {
    "positive": ('<span class="sent" style="color:#19BA5A;" title="Positive">&#9650;</span>'),
    "negative": ('<span class="sent" style="color:#F03A47;" title="Negative">&#9660;</span>'),
    "neutral": ('<span class="sent" style="color:#E89428;" title="Neutral">&#9644;</span>'),
}
ROUTE_LABELS = {
    "refund": "Refund Team",
    "safety": "Safety Team",
    "marketing": "Marketing",
    "general": "General Support",
}

IMAGES_DIR = os.path.join(
    os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"),
    "include",
    "images",
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.isdir(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def _load_from_variable():
    """Load portal data from Airflow Variable (set by plugin_sync Dag).
    Returns dict with 'reviews' and 'embeddings' keys, or None on failure."""
    try:
        return json.loads(Variable.get("support_portal_data"))
    except Exception:
        return None


def _query(sql):
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        rows = conn.execute(sql).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def _get_reviews(portal_data):
    if portal_data and "reviews" in portal_data:
        return [tuple(r) for r in portal_data["reviews"]]
    return _query(
        "SELECT r.review_id, r.review_text, r.status, r.sentiment, r.category, "
        "r.summary, r.routed_to, r.ai_response, r.submitted_at, r.approved_at, "
        "c.full_name, p.planet_name, b.passengers, pay.amount_usd, "
        "r.image_path, r.image_analysis "
        "FROM trip_reviews r "
        "JOIN bookings b ON b.booking_id = r.booking_id "
        "JOIN customers c ON c.customer_id = b.customer_id "
        "JOIN routes rt ON rt.route_id = b.route_id "
        "JOIN planets p ON p.planet_id = rt.destination_id "
        "JOIN payments pay ON pay.booking_id = b.booking_id "
        "ORDER BY r.submitted_at DESC"
    )


def _get_similar_map(portal_data):
    if portal_data and "embeddings" in portal_data:
        rows = [tuple(r) for r in portal_data["embeddings"]]
    else:
        rows = _query(
            "SELECT re.review_id, tr.category, tr.sentiment, re.embedding, tr.review_text "
            "FROM review_embeddings re "
            "JOIN trip_reviews tr ON tr.review_id = re.review_id"
        )
    if len(rows) < 2:
        return {}

    def cos(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    sim_map = {}
    for i, (rid_a, _, _, emb_a, _) in enumerate(rows):
        scored = []
        for j, (rid_b, cat_b, sent_b, emb_b, text_b) in enumerate(rows):
            if i != j:
                scored.append((rid_b, cos(emb_a, emb_b), cat_b, sent_b, text_b))
        scored.sort(key=lambda x: x[1], reverse=True)
        sim_map[rid_a] = scored[:3]
    return sim_map


def _badge(status):
    fg, bg = STATUS_COLORS.get(status, ("#6b7280", "#f3f4f6"))
    return f'<span class="badge" style="color:{fg};background:{bg};border-color:{fg};">{status}</span>'


def _tag(category):
    if not category:
        return ""
    c = CATEGORY_COLORS.get(category, "#6b7280")
    return f'<span class="tag" style="background:{c};">{category}</span>'


def _icon(sentiment):
    return SENTIMENT_ICONS.get(sentiment, "")


def _esc(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_stats(reviews):
    total = len(reviews)
    by_status = {}
    for r in reviews:
        s = r[2] or "pending"
        by_status[s] = by_status.get(s, 0) + 1

    html = ""
    for label, count, color in [
        ("Total", total, "#111827"),
        ("Pending", by_status.get("pending", 0), "#6b7280"),
        ("Analyzed", by_status.get("analyzed", 0), "#2676FF"),
        ("Routed", by_status.get("routed", 0), "#A067FB"),
        ("Drafted", by_status.get("response_drafted", 0), "#E89428"),
        ("Approved", by_status.get("approved", 0), "#19BA5A"),
        ("Rejected", by_status.get("rejected", 0), "#F03A47"),
    ]:
        html += (
            f'<div class="stat"><div class="stat-num" style="color:{color};">'
            f'{count}</div><div class="stat-label">{label}</div></div>'
        )
    return html


def _build_filters(reviews):
    all_statuses = sorted({(r[2] or "pending") for r in reviews})
    all_categories = sorted({r[4] for r in reviews if r[4]})
    all_sentiments = sorted({r[3] for r in reviews if r[3]})

    def _fbtn(group, values, cmap):
        h = f'<button class="fbtn active" data-g="{group}" data-v="all">All</button>'
        for v in values:
            c = cmap.get(v, "#111827")
            h += f'<button class="fbtn" data-g="{group}" data-v="{v}" style="--ac:{c};">{v}</button>'
        return h

    return (
        f'<div class="fg"><span class="fl">Status</span>'
        f'{_fbtn("status", all_statuses, {k: v[0] for k, v in STATUS_COLORS.items()})}</div>'
        f'<div class="fg"><span class="fl">Category</span>'
        f'{_fbtn("category", all_categories, CATEGORY_COLORS)}</div>'
        f'<div class="fg"><span class="fl">Sentiment</span>'
        f'{_fbtn("sentiment", all_sentiments, {"positive": "#19BA5A", "negative": "#F03A47", "neutral": "#E89428"})}</div>'
    )


def _build_cards(reviews, sim_map):
    if not reviews:
        return '<div style="text-align:center;padding:60px;color:#9ca3af;">No reviews found. Run the setup Dag first.</div>'

    html = ""
    for (review_id, review_text, status, sentiment, category, summary,
         routed_to, ai_response, submitted_at, approved_at,
         full_name, planet_name, passengers, amount_usd,
         image_path, image_analysis_text) in reviews:

        status = status or "pending"
        date_str = submitted_at.strftime("%b %d, %Y") if isinstance(submitted_at, datetime) else str(submitted_at)[:10]

        image_html = ""
        if image_path:
            img_file = image_path.split("/")[-1]
            image_html = (
                f'<div class="img-attach" style="margin-top:12px;">'
                f'<img src="images/{img_file}" alt="Review attachment" '
                f'style="max-width:100%;max-height:300px;border-radius:6px;border:1px solid #eee;"></div>'
            )
            if image_analysis_text:
                image_html += (
                    '<div class="sbox" style="border-left-color:#E89428;background:#fdf8f0;">'
                    f'<div class="slbl" style="color:#E89428;">IMAGE ANALYSIS</div>'
                    f'<div class="sbody">{_esc(image_analysis_text)}</div></div>'
                )

        analysis = ""
        if summary:
            analysis = (
                '<div class="sbox" style="border-left-color:#13BDD7;background:#f6fcfd;">'
                f'<div class="slbl" style="color:#13BDD7;">AI ANALYSIS</div>'
                f'<div class="sbody">{summary}</div></div>'
            )

        response = ""
        if ai_response:
            response = (
                '<div class="sbox" style="border-left-color:#19BA5A;background:#f6fdf9;">'
                f'<div class="slbl" style="color:#19BA5A;">AI DRAFTED RESPONSE</div>'
                f'<div class="sbody" style="white-space:pre-wrap;">{ai_response}</div></div>'
            )

        similar = ""
        if review_id in sim_map:
            rows_html = ""
            for sid, score, scat, ssent, stext in sim_map[review_id]:
                pct = int(score * 100)
                bc = "#19BA5A" if pct >= 70 else "#E89428" if pct >= 40 else "#6b7280"
                rows_html += (
                    f'<div class="simr">'
                    f'<span style="font-weight:600;color:#A067FB;min-width:28px;">#{sid}</span>'
                    f'{_tag(scat)} {_icon(ssent)}'
                    f'<div style="flex:1;height:5px;background:#e5e7eb;border-radius:3px;margin-left:8px;">'
                    f'<div style="height:5px;background:{bc};border-radius:3px;width:{pct}%;"></div></div>'
                    f'<span style="font-size:12px;font-weight:600;color:{bc};min-width:40px;text-align:right;">{pct}%</span>'
                    f'<div class="simtt">{_esc(stext)}</div></div>'
                )
            similar = (
                '<div class="sbox" style="border-left-color:#A067FB;background:#faf7fe;">'
                f'<div class="slbl" style="color:#A067FB;">SIMILAR REVIEWS</div>{rows_html}</div>'
            )

        routing = ""
        if routed_to:
            label = ROUTE_LABELS.get(routed_to, routed_to)
            routing = (
                '<div class="sbox" style="border-left-color:#A067FB;background:#faf7fe;">'
                f'<div class="slbl" style="color:#A067FB;">ROUTED TO</div>'
                f'<div class="sbody">{label}</div></div>'
            )

        status_box = ""
        if approved_at:
            ts = approved_at.strftime("%b %d, %Y %H:%M") if isinstance(approved_at, datetime) else str(approved_at)[:16]
            status_box = f'<div style="margin-top:8px;padding:6px 10px;background:#E2F6EA;border-radius:6px;font-size:12px;color:#19BA5A;">Approved on {ts}</div>'
        elif status == "rejected":
            status_box = '<div style="margin-top:8px;padding:6px 10px;background:#FDE9EB;border-radius:6px;font-size:12px;color:#F03A47;">AI response rejected — needs manual reply</div>'

        html += (
            f'<div class="card" data-status="{status}" data-category="{category or ""}" data-sentiment="{sentiment or ""}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">'
            f'<div><span style="font-weight:700;">#{review_id}</span>'
            f'<span style="color:#6b7280;margin-left:8px;">{full_name}</span> {_tag(category)}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;">{_icon(sentiment)} {_badge(status)}</div></div>'
            f'<div class="meta">&#127759; {planet_name} &nbsp; &#128101; {passengers} pax'
            f' &nbsp; &#128176; ${amount_usd:,} &nbsp; &#128197; {date_str}</div>'
            f'<div style="font-size:14px;color:#374151;line-height:1.6;">{review_text}</div>'
            f'{image_html}{analysis}{similar}{routing}{response}{status_box}'
            f'<div class="actions">'
            f'<button class="btn" disabled>Reply</button>'
            f'<button class="btn bd" disabled>Escalate</button>'
            f'<button class="btn" disabled>View Booking</button>'
            f'<button class="btn bg" disabled>Mark Resolved</button>'
            f'</div></div>'
        )
    return html


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    portal_data = _load_from_variable()
    reviews = _get_reviews(portal_data)
    sim_map = _get_similar_map(portal_data)
    return HTMLResponse(
        content=TEMPLATE.format(
            stats_html=_build_stats(reviews),
            filters_html=_build_filters(reviews),
            cards_html=_build_cards(reviews, sim_map),
        )
    )


class SupportPortalPlugin(AirflowPlugin):
    name = "support_portal"

    fastapi_apps = [{
        "app": app,
        "url_prefix": "/support-portal",
        "name": "AstroTrips Support Portal",
    }]
    external_views = [{
        "name": "AstroTrips",
        "href": "support-portal/dashboard",
        "icon": "support-portal/static/portal-icon.svg",
        "icon_dark_mode": "support-portal/static/portal-icon.svg",
        "destination": "nav",
        "url_route": "support-portal",
    }]
