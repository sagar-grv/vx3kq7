"""WindSight API: day-ahead UK wind forecast intelligence (Elexon FUELHH/WINDFOR, Jan 2026)."""
import datetime as dt
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import analytics
from .db import get_conn

app = FastAPI(title="WindSight API", version="1.0.0")
FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)


@app.get("/api/meta")
def meta():
    conn = get_conn()
    a = conn.execute("SELECT MIN(start_time) lo, MAX(start_time) hi, COUNT(*) n FROM actuals").fetchone()
    f = conn.execute(
        "SELECT MIN(start_time) lo, MAX(start_time) hi, MIN(publish_time) plo, MAX(publish_time) phi, COUNT(*) n FROM forecasts"
    ).fetchone()
    return {
        "product": "WindSight",
        "scope": "GB wind (Elexon FUELHH half-hourly generation outturn, fuelType=WIND; WINDFOR wind generation forecast). Delivery days: January 2026.",
        "actuals": {"from": a["lo"], "to": a["hi"], "records": a["n"]},
        "forecasts": {"from": f["lo"], "to": f["hi"], "published_from": f["plo"], "published_to": f["phi"], "records": f["n"]},
    }


@app.get("/api/days")
def days():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT substr(start_time, 1, 10) AS d FROM actuals ORDER BY d").fetchall()
    return {"days": [r["d"] for r in rows]}


@app.get("/api/summary")
def summary(cutoff: str = Query("23:00")):
    """Retrospective accuracy over the full month (all forecast versions), plus the
    day-ahead decision set: the single latest forecast at the D-1 cutoff per hour."""
    conn = get_conn()
    pairs = analytics.error_pairs(conn)
    overall = analytics.metrics([p["error"] for p in pairs], [p["actual"] for p in pairs])
    days_rows = conn.execute("SELECT DISTINCT substr(start_time, 1, 10) AS d FROM actuals ORDER BY d").fetchall()
    decision = []
    for r in days_rows:
        for pt in analytics.day_ahead_points(conn, dt.date.fromisoformat(r["d"]), cutoff):
            if pt["error"] is not None:
                decision.append(pt)
    decision_metrics = analytics.metrics([p["error"] for p in decision], [p["actual"] for p in decision])
    return {
        "overall": overall,
        "by_horizon": analytics.by_horizon(pairs),
        "decision_set": {
            "description": f"Only the single latest forecast per delivery hour as of the D-1 {cutoff} UTC cutoff - the version a desk would actually have used.",
            "cutoff": cutoff,
            **decision_metrics,
        },
    }


@app.get("/api/day-ahead")
def day_ahead(date: str = Query(...), cutoff: str = Query("23:00")):
    try:
        d = dt.date.fromisoformat(date)
        dt.time.fromisoformat(cutoff)
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD and cutoff HH:MM")
    conn = get_conn()
    points = analytics.day_ahead_points(conn, d, cutoff)
    if not points:
        raise HTTPException(404, f"no data for delivery day {date}")
    fc_pts = [p for p in points if p["forecast"] is not None]
    both = [p for p in points if p["forecast"] is not None and p["actual"] is not None]
    forecast_mwh = sum(p["forecast"] for p in fc_pts)  # hourly MW == MWh per hour
    actual_mwh = sum(p["actual"] for p in points if p["actual"] is not None)
    m = analytics.metrics([p["error"] for p in both], [p["actual"] for p in both])
    return {
        "date": date,
        "cutoff_utc": f"{(d - dt.timedelta(days=1)).isoformat()}T{cutoff}:00Z",
        "band": {
            "calibration": f"P10-P90 of forecast errors published in the {analytics.BAND_CALIBRATION_DAYS} days before the cutoff, same horizon bucket. Uses only information available at decision time (no lookahead).",
            "days": analytics.BAND_CALIBRATION_DAYS,
        },
        "points": points,
        "totals": {
            "forecast_mwh": round(forecast_mwh, 0),
            "actual_mwh": round(actual_mwh, 0),
            "energy_error_mwh": round(forecast_mwh - actual_mwh, 0),
            **m,
        },
    }


@app.get("/api/evolution")
def evolution(start_time: str = Query(..., description="Target hour, e.g. 2026-01-15T14:00:00Z")):
    conn = get_conn()
    try:
        analytics.parse(start_time)
    except ValueError:
        raise HTTPException(400, "start_time must be ISO, e.g. 2026-01-15T14:00:00Z")
    rows = conn.execute(
        "SELECT publish_time, generation FROM forecasts WHERE start_time = ? ORDER BY publish_time",
        (start_time,),
    ).fetchall()
    actuals = analytics.hourly_actuals(conn)
    actual = actuals.get(start_time[:13])
    if not rows and actual is None:
        raise HTTPException(404, f"no data for {start_time}")
    st = analytics.parse(start_time)
    versions = [
        {
            "publish_time": r["publish_time"],
            "generation": r["generation"],
            "horizon_h": round((st - analytics.parse(r["publish_time"])).total_seconds() / 3600.0, 1),
            "error": round(r["generation"] - actual, 1) if actual is not None else None,
        }
        for r in rows
        if (st - analytics.parse(r["publish_time"])).total_seconds() >= 0
    ]
    return {
        "start_time": start_time,
        "actual": round(actual, 1) if actual is not None else None,
        "versions": versions,
    }


@app.get("/api/accuracy/daily")
def accuracy_daily(cutoff: str = Query("23:00")):
    conn = get_conn()
    days_rows = conn.execute("SELECT DISTINCT substr(start_time, 1, 10) AS d FROM actuals ORDER BY d").fetchall()
    out = []
    for r in days_rows:
        d = dt.date.fromisoformat(r["d"])
        pts = analytics.day_ahead_points(conn, d, cutoff)
        both = [p for p in pts if p["error"] is not None]
        if not both:
            continue
        m = analytics.metrics([p["error"] for p in both], [p["actual"] for p in both])
        out.append({"date": r["d"], **m})
    return {"cutoff": cutoff, "days": out}


@app.get("/api/accuracy/distribution")
def accuracy_distribution(bin_width: int = Query(500, ge=100, le=5000)):
    conn = get_conn()
    pairs = analytics.error_pairs(conn)
    # Day-ahead decision class: forecasts published 12-36 h before delivery
    da = [p["error"] for p in pairs if 12 <= p["horizon_h"] < 36]
    if not da:
        return {"bin_width": bin_width, "bins": [], "n": 0}
    lo = int(min(da) // bin_width) * bin_width
    hi = int(max(da) // bin_width) * bin_width + bin_width
    bins = []
    b = lo
    while b < hi:
        n = sum(1 for e in da if b <= e < b + bin_width)
        bins.append({"from": b, "to": b + bin_width, "count": n})
        b += bin_width
    q10, q90 = analytics.quantiles(da, (0.1, 0.9))
    return {"bin_width": bin_width, "bins": bins, "n": len(da), "p10": round(q10, 1), "p90": round(q90, 1)}


# --- static frontend (SPA) ---
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
