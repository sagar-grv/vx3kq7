import datetime as dt

from app import analytics


def test_bucket_for():
    assert analytics.bucket_for(0) == "0-6 h"
    assert analytics.bucket_for(5.9) == "0-6 h"
    assert analytics.bucket_for(6) == "6-12 h"
    assert analytics.bucket_for(23.9) == "18-24 h"
    assert analytics.bucket_for(47.9) == "36-48 h"
    assert analytics.bucket_for(48) == ">48 h"
    assert analytics.bucket_for(200) == ">48 h"


def test_metrics_basic():
    m = analytics.metrics([10, -10, 20, -20], [100, 100, 100, 100])
    assert m["n"] == 4
    assert m["mae"] == 15.0
    assert m["bias"] == 0.0
    assert m["mape"] == 15.0
    assert m["rmse"] == 15.8


def test_metrics_empty():
    m = analytics.metrics([])
    assert m["n"] == 0 and m["mae"] is None and m["rmse"] is None


def test_quantiles():
    q10, q90 = analytics.quantiles(list(range(0, 101)), (0.1, 0.9))
    assert q10 == 10 and q90 == 90


def test_iso_parse_roundtrip():
    d = dt.datetime(2026, 1, 15, 14, 0, tzinfo=dt.timezone.utc)
    assert analytics.parse(analytics.iso(d)) == d
