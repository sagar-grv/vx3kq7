"""No-lookahead calibration: forecasts published before the cutoff but targeting
hours whose outturn was NOT yet published at the cutoff must be excluded."""
import datetime as dt
import sqlite3

from app import analytics
from app.db import init_db


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _add_actual(conn, start_time, mw):
    d, _ = start_time.split("T")
    sp = (int(start_time[11:13]) * 2) + (1 if start_time[14:16] == "00" else 2)
    conn.execute(
        "INSERT OR REPLACE INTO actuals (start_time, settlement_date, settlement_period, generation) VALUES (?,?,?,?)",
        (start_time, d, sp, mw),
    )


def test_calibration_excludes_future_actuals_and_late_publishes():
    conn = _conn()
    # Actuals for all of 2026-01-14 and 2026-01-15
    for day in ("2026-01-14", "2026-01-15"):
        for h in range(24):
            _add_actual(conn, f"{day}T{h:02d}:00:00Z", 5000.0)
            _add_actual(conn, f"{day}T{h:02d}:30:00Z", 5000.0)
    # Calibration candidates, all published 2026-01-13T12:00Z (before cutoff):
    # (a) targets on 2026-01-14 hours 0..20 -> usable (outturn published before cutoff)
    for h in range(21):
        conn.execute(
            "INSERT INTO forecasts VALUES (?,?,?)",
            (f"2026-01-14T{h:02d}:00:00Z", "2026-01-13T12:00:00Z", 5100.0),  # error +100
        )
    # (b) targets on 2026-01-15 (after cutoff) -> MUST be excluded despite publish < cutoff
    for h in range(24):
        conn.execute(
            "INSERT INTO forecasts VALUES (?,?,?)",
            (f"2026-01-15T{h:02d}:00:00Z", "2026-01-13T12:00:00Z", 14000.0),  # error +9000
        )
    # (c) published after cutoff targeting a past hour -> excluded by publish filter
    conn.execute(
        "INSERT INTO forecasts VALUES (?,?,?)",
        ("2026-01-14T10:00:00Z", "2026-01-15T01:00:00Z", 14000.0),
    )
    # Day-ahead forecasts the desk would use for 2026-01-15 (latest before cutoff)
    for h in range(24):
        conn.execute(
            "INSERT INTO forecasts VALUES (?,?,?)",
            (f"2026-01-15T{h:02d}:00:00Z", "2026-01-14T22:30:00Z", 5000.0),
        )
    conn.commit()

    analytics.BAND_MIN_PAIRS = 3  # small synthetic set
    points = analytics.day_ahead_points(conn, dt.date(2026, 1, 15), "23:00")
    cal = analytics.day_ahead_points.last_calibration

    # Only the 21 usable +100-error pairs may be in the calibration set
    assert cal["pairs"] == 21, cal
    # Bucket 12-18 h holds calibration errors of exactly +100 -> band pins to it
    p14 = next(p for p in points if p["hour"] == "2026-01-15T14:00:00Z")  # horizon 15.5h
    assert p14["band_low"] == 5100.0 and p14["band_high"] == 5100.0
    # Bucket 0-6 h has no usable pairs -> band unavailable, never a full-month fallback
    p00 = next(p for p in points if p["hour"] == "2026-01-15T00:00:00Z")  # horizon 1.5h
    assert p00["band_low"] is None and p00["band_high"] is None
    # If the +9000 errors leaked in, every band would be far above 5100 - asserted above.


def test_calibration_limited_history_flag():
    conn = _conn()
    for h in range(24):
        _add_actual(conn, f"2026-01-15T{h:02d}:00:00Z", 5000.0)
        _add_actual(conn, f"2026-01-15T{h:02d}:30:00Z", 5000.0)
        conn.execute(
            "INSERT INTO forecasts VALUES (?,?,?)",
            (f"2026-01-15T{h:02d}:00:00Z", "2026-01-14T22:30:00Z", 5000.0),
        )
    conn.commit()
    analytics.BAND_MIN_PAIRS = 30
    points = analytics.day_ahead_points(conn, dt.date(2026, 1, 15), "23:00")
    assert analytics.day_ahead_points.last_calibration["pairs"] == 0
    assert all(p["band_low"] is None for p in points)
