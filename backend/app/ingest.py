"""Ingest January 2026 UK national wind data from the Elexon BMRS Insights API.

- Actuals:  dataset FUELHH, fuelType=WIND, half-hourly, filtered by settlement date.
- Forecasts: dataset WINDFOR, hourly, fetched by publish date so every forecast
  version issued for January 2026 delivery hours is captured.

Only data relevant to day-ahead purchase decisions for delivery days in
January 2026 is stored: delivery hours 2026-01-01T00:00Z .. 2026-02-01T00:00Z.
Forecasts are pulled for publish dates 2025-12-29 .. 2026-02-01 so that
day-ahead (and earlier) forecast versions for those hours are all present.
"""
import datetime as dt

import httpx

from .db import get_conn

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DELIVERY_START = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
DELIVERY_END = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)  # exclusive
PUBLISH_START = dt.date(2025, 12, 29)
PUBLISH_END = dt.date(2026, 2, 1)  # inclusive
TIMEOUT = httpx.Timeout(60.0)


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fetch_fuelhh_day(client: httpx.Client, day: dt.date) -> list[dict]:
    resp = client.get(
        f"{BASE}/FUELHH",
        params={
            "settlementDateFrom": day.isoformat(),
            "settlementDateTo": day.isoformat(),
            "fuelType": "WIND",
        },
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_windfor_day(client: httpx.Client, publish_day: dt.date) -> list[dict]:
    resp = client.get(
        f"{BASE}/WINDFOR",
        params={
            "publishDateTimeFrom": f"{publish_day.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{publish_day.isoformat()}T23:59:59Z",
        },
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def ingest() -> None:
    conn = get_conn()
    with httpx.Client(timeout=TIMEOUT) as client:
        # Actuals: every delivery day in January 2026
        day = DELIVERY_START.date()
        n_actual = 0
        while day < DELIVERY_END.date():
            rows = fetch_fuelhh_day(client, day)
            conn.executemany(
                "INSERT OR REPLACE INTO actuals (start_time, settlement_date, settlement_period, generation)"
                " VALUES (?, ?, ?, ?)",
                [
                    (r["startTime"], r["settlementDate"], r["settlementPeriod"], float(r["generation"]))
                    for r in rows
                ],
            )
            conn.commit()
            n_actual += len(rows)
            print(f"FUELHH {day}: {len(rows)} rows")
            day += dt.timedelta(days=1)

        # Forecasts: every publish day that can hold a version targeting January delivery hours
        pday = PUBLISH_START
        n_fore = 0
        while pday <= PUBLISH_END:
            rows = fetch_windfor_day(client, pday)
            kept = []
            for r in rows:
                st = _parse(r["startTime"])
                if DELIVERY_START <= st < DELIVERY_END:
                    kept.append((r["startTime"], r["publishTime"], float(r["generation"])))
            conn.executemany(
                "INSERT OR REPLACE INTO forecasts (start_time, publish_time, generation) VALUES (?, ?, ?)",
                kept,
            )
            conn.commit()
            n_fore += len(kept)
            print(f"WINDFOR published {pday}: {len(rows)} rows, {len(kept)} kept")
            pday += dt.timedelta(days=1)
    print(f"Done. actuals={n_actual} forecasts_kept={n_fore}")


if __name__ == "__main__":
    ingest()
