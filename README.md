# WindSight - Day-ahead UK wind forecast intelligence

Pilot build for a UK energy utility's day-ahead purchasing desk. The desk must decide,
one day before each delivery day, how much power to procure beyond what the national
wind fleet will generate. WindSight answers the two questions that decision depends on:

1. **What is the latest wind forecast available at decision time?**
   The Day-Ahead Desk view shows, for any January 2026 delivery day, exactly the forecast
   versions the desk could see at a configurable D-1 decision cutoff, next to what the
   wind fleet actually generated - with an empirical P10-P90 error band per horizon.
   The band is calibrated strictly without lookahead: only the trailing 14 days of
   forecast/actual pairs where BOTH the forecast and the actual were available by the
   cutoff (actuals assumed published within 2 h of each hour's end; configurable via
   CAL_ACTUAL_LAG_HOURS). With fewer than 30 usable pairs (CAL_BAND_MIN_PAIRS) the desk
   shows a "limited history" notice instead of a band - never a full-month fallback.
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

Interpretation caveat: the app quantifies forecast error only. Under a simple
fixed-demand assumption (buy residual = demand minus forecast wind), a positive error
- an over-forecast - means the desk would have bought too little residual power
(shortfall exposure); a negative error means surplus. No financial impact is claimed:
demand volumes and market prices are outside the dataset.

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

### With Docker

The brief asks for a Docker deliverable, so a multi-stage Dockerfile and a compose
wrapper are included:

```sh
docker build -t windsight .
docker run -p 8000:8000 windsight
# open http://localhost:8000
```

or `docker compose up --build`.

**Verification status: verified by CI.** The `docker-verify` GitHub Actions workflow (`.github/workflows/docker-verify.yml`) builds this image on every push, runs the backend pytest suite inside the container, and smoke-tests the served endpoints (`/api/meta` and `/`). Latest run on `main`: passing (repo Actions tab). During development the image steps were also replicated and verified manually (clean `npm install && npm run build`, clean venv from `requirements.txt`, entrypoint env handling, and every API endpoint against the served static bundle).

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

Live deployment (Vercel free tier): static frontend build plus the FastAPI app as a serverless function (`api/index.py` + `vercel.json`). The production deployment is verified live: the app loads and `/api/meta` serves the bundled January 2026 dataset.

Deployed URL: **https://vx3kq7.vercel.app**

## AI usage disclosure

Per the challenge brief's permission to use AI tools with disclosure: this application
was built with extensive AI coding assistance throughout - project scaffolding, the
analytics implementation, the test suite, debugging, the data ingestion work, and the
documentation. The author directed the work and set the requirements.

Independently of how the code was produced: all data shown is fetched from the Elexon
BMRS Insights API and computed by the code in this repository; no results are
hand-written or invented. Every headline figure can be reproduced by running the tests
and the audit script (`backend/audit.py`) against the bundled dataset.
