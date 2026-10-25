# WindSight - Day-ahead UK wind forecast intelligence

Pilot build for a UK energy utility's day-ahead purchasing desk. The desk must decide,
one day before each delivery day, how much power to procure beyond what the national
wind fleet will generate. WindSight answers the two questions that decision depends on:

1. **What is the latest wind forecast available at decision time?**
   The Day-Ahead Desk view shows, for any January 2026 delivery day, exactly the forecast
   versions the desk could see at a configurable D-1 decision cutoff, next to what the
   wind fleet actually generated - with an empirical P10-P90 error band per horizon.
2. **How accurate are those forecasts, quantitatively?**
   The Accuracy Analytics view scores every forecast version issued for January 2026
   delivery hours against the final actuals: MAE / RMSE / bias / MAPE overall and by
   forecast horizon, day-ahead MAE by delivery day, and the day-ahead error distribution.
   A Forecast Evolution view shows every published version for a single delivery hour
   converging on the actual.

## Data

Only Elexon national wind data is used, and only data relevant to purchase decisions
for delivery days in **January 2026**:

- Actuals: BMRS Insights `FUELHH` dataset - half-hourly generation outturn by fuel type
  for Great Britain; we use `fuelType=WIND`, average MW per 30-minute settlement period
  (https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- Forecasts: BMRS Insights `WINDFOR` dataset - wind generation forecast, hourly, every
  publish version retained
  (https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)

Coverage basis (verified against Elexon/NESO documentation): FUELHH outturn comes from
Operational Metering of transmission-system BMUs; Elexon notes renewables outturn excludes
embedded and operationally unmetered wind farms (NESO estimates roughly 82% coverage as of
2025). NESO describes its wind forecast as the "operational metered wind forecast", the same
metering basis, so forecast and actual are compared like-for-like. Total GB wind including
embedded generation is out of scope, exactly as the brief specifies (Elexon data only).

Dataset bundled in `data/wind.db`: 1,488 actual half-hours and 18,104 forecast versions
(published 2025-12-30 to 2026-02-01) covering delivery hours 2026-01-01 to 2026-01-31 (UTC).

Method: forecasts (hourly) are aligned with actuals (mean of the two half-hour settlement
periods in each hour, UTC). Error = forecast - actual (positive = over-forecast).
Horizon = hours between forecast publish time and delivery start time.
Metrics: MAPE is the pointwise mean |error|/actual (hours under 100 MW actual excluded);
nMAE/WAPE is MAE / mean actual. The Day-Ahead Desk P10-P90 band is calibrated only on
forecast versions published in the 14 days before the chosen cutoff (no lookahead);
the Accuracy Analytics page is a retrospective full-month analysis.

## Files and directories

```
Dockerfile               Multi-stage image: builds the React app, serves it from FastAPI
docker-compose.yml       One-service convenience wrapper (docker compose up)
scripts/entrypoint.sh    Container start: ingest if the DB is missing, then serve
backend/
  requirements.txt       FastAPI + uvicorn + httpx
  app/db.py              SQLite schema and connection helpers
  app/ingest.py          Pulls January 2026 FUELHH (WIND) and WINDFOR from Elexon
  app/analytics.py       Hourly alignment, error metrics, horizon buckets, day-ahead logic
  app/main.py            API routes (/api/...) and static hosting of the built frontend
  tests/test_analytics.py  Unit tests for the analytics core (no network)
frontend/
  package.json, vite.config.js, index.html
  src/App.jsx            Shell: header, tab navigation
  src/api.js             API client
  src/pages/DayAhead.jsx   Day-ahead desk: forecast-vs-actual chart, error band, hourly table
  src/pages/Evolution.jsx  Forecast evolution for one delivery hour
  src/pages/Accuracy.jsx   Accuracy analytics: by horizon, by day, error distribution
  src/components/StatCard.jsx
  src/styles.css
data/wind.db             Bundled SQLite dataset (see Data). Rebuild with the ingest command below
```

## How to start

### With Docker (recommended)

```sh
docker build -t windsight .
docker run -p 8000:8000 windsight
# open http://localhost:8000
```

or `docker compose up --build`.

The bundled database is included in the image. If it is deleted, the container
re-ingests January 2026 from Elexon on startup (requires outbound network).

### Local development

Backend (Python 3.10+):

```sh
cd backend
pip install -r requirements.txt
PYTHONPATH=. python -m app.ingest      # one-time data pull (or copy data/wind.db)
PYTHONPATH=. uvicorn app.main:app --port 8377
```

Frontend (Node 18+):

```sh
cd frontend
npm install
npm run dev                            # proxies /api to localhost:8377
# or: npm run build  -> served by the backend at /
```

Tests: `cd backend && PYTHONPATH=. python -m pytest tests/ -q`

## Deployed app

The app is deployed as a single container (see Dockerfile) at: **APP_URL_PLACEHOLDER**

## AI usage disclosure

AI coding assistance was used to build this application (scaffolding, boilerplate,
chart configuration, and documentation drafting), as permitted by the challenge brief.
All data shown is fetched from the Elexon BMRS Insights API and computed by the code in
this repository; no results are hand-written.
