"""Forecast-vs-actual alignment and accuracy analytics.

Resolution: WINDFOR forecasts are hourly; FUELHH actuals are half-hourly.
We align on whole hours (UTC): the actual for hour H is the mean of the two
settlement periods starting at H:00 and H:30.

Error convention: error = forecast - actual (positive = over-forecast).
Horizon: whole hours between publish_time and start_time.
"""
import datetime as dt
import math
import statistics
from typing import Iterable, Optional

HORIZON_BUCKETS = [
    (0, 6, "0-6 h"),
    (6, 12, "6-12 h"),
    (12, 18, "12-18 h"),
    (18, 24, "18-24 h"),
    (24, 36, "24-36 h"),
    (36, 48, "36-48 h"),
    (48, 10_000, ">48 h"),
]


def bucket_for(horizon_h: float) -> str:
    for lo, hi, label in HORIZON_BUCKETS:
        if lo <= horizon_h < hi:
            return label
    return HORIZON_BUCKETS[-1][2]


def parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def iso(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hourly_actuals(conn) -> dict[str, float]:
    """Map hour-start ISO -> mean MW of the two half-hour periods in that hour."""
    rows = conn.execute(
        "SELECT substr(start_time, 1, 13) AS hour, AVG(generation) AS g, COUNT(*) AS n"
        " FROM actuals GROUP BY hour"
    ).fetchall()
    return {r["hour"]: r["g"] for r in rows if r["n"] > 0}


def error_pairs(conn) -> list[dict]:
    """All (forecast version, actual) pairs for hours that have an actual."""
    actuals = hourly_actuals(conn)
    pairs = []
    for r in conn.execute("SELECT start_time, publish_time, generation FROM forecasts"):
        hour = r["start_time"][:13]
        if hour not in actuals:
            continue
        st, pt = parse(r["start_time"]), parse(r["publish_time"])
        horizon_h = (st - pt).total_seconds() / 3600.0
        if horizon_h < 0:
            continue  # forecast published after the fact: not usable for decisions
        actual = actuals[hour]
        pairs.append(
            {
                "start_time": r["start_time"],
                "publish_time": r["publish_time"],
                "forecast": r["generation"],
                "actual": actual,
                "error": r["generation"] - actual,
                "horizon_h": horizon_h,
                "bucket": bucket_for(horizon_h),
            }
        )
    return pairs


def metrics(errors: Iterable[float], actuals: Optional[Iterable[float]] = None) -> dict:
    errs = list(errors)
    if not errs:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "mape": None}
    mae = sum(abs(e) for e in errs) / len(errs)
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    bias = sum(errs) / len(errs)
    mape = None
    if actuals is not None:
        acts = [a for a in actuals if a and a > 0]
        if acts:
            mape = 100.0 * mae / (sum(acts) / len(acts))
    return {"n": len(errs), "mae": round(mae, 1), "rmse": round(rmse, 1), "bias": round(bias, 1), "mape": round(mape, 2) if mape is not None else None}


def by_horizon(pairs: list[dict]) -> list[dict]:
    out = []
    for _, _, label in HORIZON_BUCKETS:
        rows = [p for p in pairs if p["bucket"] == label]
        m = metrics([p["error"] for p in rows], [p["actual"] for p in rows])
        out.append({"bucket": label, **m})
    return out


def quantiles(values: list[float], qs=(0.1, 0.9)) -> list[Optional[float]]:
    if not values:
        return [None for _ in qs]
    vals = sorted(values)
    return [vals[min(len(vals) - 1, max(0, round(q * (len(vals) - 1))))] for q in qs]


def latest_forecasts_before(conn, cutoff: dt.datetime) -> dict[str, dict]:
    """Latest published forecast per target hour, restricted to publish_time <= cutoff."""
    rows = conn.execute(
        "SELECT f.start_time, f.publish_time, f.generation FROM forecasts f"
        " JOIN (SELECT start_time, MAX(publish_time) AS mp FROM forecasts WHERE publish_time <= ? GROUP BY start_time) latest"
        " ON f.start_time = latest.start_time AND f.publish_time = latest.mp",
        (iso(cutoff),),
    ).fetchall()
    return {r["start_time"]: {"publish_time": r["publish_time"], "generation": r["generation"]} for r in rows}


def day_ahead_points(conn, date: dt.date, cutoff_hhmm: str) -> list[dict]:
    """For delivery day `date`, the forecast the desk would see at the D-1 cutoff, vs actuals."""
    hh, mm = (int(x) for x in cutoff_hhmm.split(":"))
    cutoff = dt.datetime.combine(date - dt.timedelta(days=1), dt.time(hh, mm, tzinfo=dt.timezone.utc))
    latest = latest_forecasts_before(conn, cutoff)
    actuals = hourly_actuals(conn)
    # Empirical error band per horizon bucket across the whole dataset
    pairs = error_pairs(conn)
    bands = {}
    for _, _, label in HORIZON_BUCKETS:
        errs = [p["error"] for p in pairs if p["bucket"] == label]
        bands[label] = quantiles(errs, (0.1, 0.9))
    points = []
    for hour in range(24):
        st = dt.datetime.combine(date, dt.time(hour, tzinfo=dt.timezone.utc))
        st_iso = iso(st)
        fc = latest.get(st_iso)
        actual = actuals.get(st_iso[:13])
        if fc is None and actual is None:
            continue
        horizon_h = (st - parse(fc["publish_time"])).total_seconds() / 3600.0 if fc else None
        bucket = bucket_for(horizon_h) if horizon_h is not None else None
        q10, q90 = bands.get(bucket, (None, None)) if bucket else (None, None)
        points.append(
            {
                "hour": st_iso,
                "actual": round(actual, 1) if actual is not None else None,
                "forecast": fc["generation"] if fc else None,
                "publish_time": fc["publish_time"] if fc else None,
                "horizon_h": round(horizon_h, 1) if horizon_h is not None else None,
                "error": round(fc["generation"] - actual, 1) if (fc and actual is not None) else None,
                "band_low": round(fc["generation"] + q10, 1) if (fc and q10 is not None) else None,
                "band_high": round(fc["generation"] + q90, 1) if (fc and q90 is not None) else None,
            }
        )
    return points
