# WindSight demo video script (unlisted YouTube, max 10 minutes total)

Two parts, per the challenge brief. Part 1 = client pitch (pilot project output, goal: impress),
max 5-minute initial overview. Part 2 = technical review for the tech lead (architecture, design,
analysis, code base, key development practices; goal: easy review + knowledge transfer), max
5-minute initial overview. Record screen at 1080p; speak over it.

## PART 1 - Client pitch (target ~4:30)

**Shot 1 (0:00-0:30) - Title + one-liner**
Show the app header. Say:
"This is WindSight, the pilot we built for your day-ahead purchasing desk. Every day your team
decides how much power to buy beyond what the wind fleet will deliver - and that decision is
only as good as the wind forecast behind it. WindSight puts the latest forecast in front of you
at decision time, and tells you exactly how much you can trust it."

**Shot 2 (0:30-1:50) - Day-Ahead Desk**
Open Day-Ahead Desk, delivery day 2026-01-15, cutoff 23:00. Say:
"Here is your decision view. Pick the delivery day and your decision cutoff - this shows the
latest forecast Elexon had published by that cutoff, nothing you couldn't have seen, plotted
against what the fleet actually generated. For the 15th of January, the day-ahead forecast was
284.9 GWh against 253.6 GWh actual: a +31.3 GWh over-forecast. If you had procured against the
raw forecast, you would have over-bought by roughly that amount. The dashed band is the
empirical P10-P90 error range for forecasts at this horizon, learned from all of January - so
you buy against a range, not a point. The table below is the hourly detail behind the chart."

**Shot 3 (1:50-3:00) - Accuracy Analytics**
Switch to Accuracy Analytics. Say:
"How much can you trust the forecast in general? We scored every forecast version issued for
January delivery - over fourteen thousand - against final actuals. Mean absolute error is
about 2.1 GW per hour, MAPE about 18 percent, and there is a systematic bias of about +1.7 GW:
the forecast over-predicts wind on average. Error grows with horizon, as you'd expect, which is
exactly why the day-ahead cutoff matters. The daily view shows which delivery days were hard -
and the distribution shows eighty percent of day-ahead hourly forecasts land inside this band,
which is the band you saw on the desk view."

**Shot 4 (3:00-4:00) - Forecast Evolution**
Switch to Forecast Evolution, 2026-01-15 18:00. Say:
"For any single delivery hour you can watch the forecast converge. For this evening peak hour,
the earliest version, sixty-three hours out, was nearly 3 GW too high; by two and a half hours
before delivery the error was under 700 MW. This is why we anchor decisions to the latest
forecast at your cutoff - and why we quantify the rest."

**Shot 5 (4:00-4:30) - Close**
Back to Day-Ahead Desk. Say:
"Everything you see is computed live from Elexon's national wind actuals and forecasts, and
nothing else - no synthetic data. The natural next step for production is wiring in your demand
forecast and market prices so the error band becomes a procurement recommendation in megawatts
and pounds. Happy to walk your team through it."

## PART 2 - Technical review (target ~4:30)

**Shot 1 (0:00-0:45) - Architecture**
Show README file tree in the repo. Say:
"Two-tier app: a React front end, a Python FastAPI back end, and SQLite for storage. One
Dockerfile builds the front end with a Node stage and serves the static bundle from FastAPI,
so the whole app ships as a single container - the same artifact runs locally, on Heroku, or
any container host. Docker Compose is included as a convenience wrapper."

**Shot 2 (0:45-1:50) - Data pipeline**
Show backend/app/ingest.py. Say:
"Ingestion pulls from the Elexon BMRS Insights API only. Actuals come from the FUELHH dataset,
fuel type WIND, half-hourly, by settlement date. Forecasts come from WINDFOR, pulled by publish
date so we retain every forecast version, not just the latest - that history is what powers the
accuracy analytics. We keep only delivery hours in January 2026, per the brief, plus the
forecast versions published for them from late December. The dataset is bundled in the repo as
a SQLite file, so the container starts deterministically; if the file is missing, the entry
point re-ingests from Elexon."

**Shot 3 (1:50-2:50) - Analytics core**
Show backend/app/analytics.py. Say:
"Forecasts are hourly; actuals are half-hourly, so we align on whole hours, UTC - January has
no DST complications. Error is forecast minus actual, so a positive error is an over-forecast
and an over-procurement risk. Horizon is publish-to-delivery time, bucketed zero to six,
six to twelve, and so on. The day-ahead view is a point-in-time join: for each delivery hour,
the latest version published at or before the decision cutoff - no lookahead, which matters
because it means the accuracy figures are what a desk would actually have experienced. Error
bands are empirical P10-P90 quantiles per horizon bucket."

**Shot 4 (2:50-3:50) - API + front end**
Show backend/app/main.py, then frontend/src/pages/DayAhead.jsx. Say:
"The API is small and read-only: meta, day list, day-ahead points, forecast evolution, and
accuracy aggregates. The front end is React with Recharts - three views matching the three
questions: what do I see at decision time, how did the forecast evolve, and how accurate is it
overall. State is local; every view is a direct function of the API responses."

**Shot 5 (3:50-4:30) - Practices + close**
Show tests and Dockerfile. Say:
"The analytics core has unit tests independent of the network. The database layer is idempotent
- re-ingestion upserts, so it's safe to re-run. Configuration is by environment variables:
port, database path, front-end directory. Known limits: SQLite fits a one-month pilot but a
production build would move to Postgres; horizon bucketing is hourly, matching the forecast
resolution; and the app is read-only by design - no write surface to secure for a pilot.
Happy to take questions on any part of the code."

## Pre-upload checklist
- [ ] Video unlisted, max 10:00 total; Part 1 and Part 2 each start with an overview <= 5:00
- [ ] Open the app, repo, and video links in an incognito window to verify access
- [ ] No personal identifiers in the public repo (brief requires an anonymous repo name)
