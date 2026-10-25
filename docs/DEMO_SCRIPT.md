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
at decision time, and quantifies how accurate those forecasts have actually been."

**Shot 2 (0:30-1:50) - Day-Ahead Desk**
Open Day-Ahead Desk, delivery day 2026-01-15, cutoff 23:00. Say:
"Here is your decision view. Pick the delivery day and your decision cutoff - this shows the
latest forecast Elexon had published by that cutoff, nothing you couldn't have seen, plotted
against what the fleet actually generated. For the 15th of January, the day-ahead forecast was
284.9 GWh against 253.6 GWh actual: a +31.3 GWh over-forecast. Under a simple fixed-demand
assumption - buying residual volume equal to demand minus forecast wind - procuring against
the raw forecast would have left the desk roughly 31 GWh short on the day, to be covered in
the balancing market. We deliberately don't put a pound figure on that: demand and price data
are outside this pilot's dataset. The dashed band is the empirical P10-P90 error range for
forecasts at this horizon, calibrated only on the prior fourteen days and only on hours whose
actuals were also published by the cutoff - so it uses nothing the desk would not have had at
decision time. The table below is the hourly detail behind the chart."

**Shot 3 (1:50-3:00) - Accuracy Analytics**
Switch to Accuracy Analytics. Say:
"How accurate is the forecast in general? We scored every forecast version issued for
January delivery - over fourteen thousand - against final actuals. This is a retrospective full-month calibration. Mean absolute
error is about 2.1 GW per hour, MAPE about 21 percent pointwise, and there is a systematic
bias of about +1.7 GW:
the forecast over-predicts wind on average. Error grows with horizon, as you'd expect, which is
exactly why the day-ahead cutoff matters. The daily view shows which delivery days were hard -
and the distribution shows about eighty percent of January's day-ahead hourly errors falling
between the P10 and P90 quantiles - that is by construction of a P10-P90 range, so read it as
a description of this month, not a validated coverage guarantee. And for the single latest
forecast you would actually have used at an 11pm cutoff the night before, the MAE is about
1.9 GW - that is the accuracy the desk would actually have experienced. It is a descriptive
measure, not a procurement margin rule: sizing a margin would need demand and price data we
don't model here."

**Shot 4 (3:00-4:00) - Forecast Evolution**
Switch to Forecast Evolution, 2026-01-15 18:00. Say:
"For any single delivery hour you can watch the forecast converge. For this evening peak hour,
the earliest version, sixty-three hours out, was nearly 3 GW too high; by two and a half hours
before delivery the error was under 700 MW. This is why we anchor decisions to the latest
forecast at your cutoff - and why we quantify the rest."

**Shot 5 (4:00-4:30) - Close**
Back to Day-Ahead Desk. Say:
"Everything you see is computed by the app's analytics code from a bundled snapshot of
Elexon's national wind actuals and forecasts for January 2026, pulled from Elexon's API at
ingest time - no synthetic data. The natural next step for production is wiring in your demand
forecast and market prices so the error band becomes a procurement recommendation in megawatts
and pounds. Happy to walk your team through it."

## PART 2 - Technical review (target ~4:30)

**Shot 1 (0:00-0:45) - Architecture**
Show README file tree in the repo. Say:
"Two-tier app: a React front end, a Python FastAPI back end, and SQLite for storage. One
Dockerfile builds the front end with a Node stage and serves the static bundle from FastAPI,
so the whole app can ship as a single container. Full disclosure: the build environment had no
Docker daemon, so the image build itself is not yet verified - every step in the Dockerfile
was replicated and tested manually instead. The deployment route for the pilot is Vercel:
static front end plus the FastAPI app as a serverless function, and the config is already in
the repo. Docker Compose is included as a convenience wrapper."

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
which, under the fixed-demand assumption, is an under-procurement or shortfall risk for the
desk. Horizon is publish-to-delivery time, bucketed zero to six,
six to twelve, and so on. The day-ahead view is a point-in-time join: for each delivery hour,
the latest version published at or before the decision cutoff - no lookahead, which matters
because it means the accuracy figures are what a desk would actually have experienced. Error
bands are empirical P10-P90 quantiles per horizon bucket, calibrated on the trailing fourteen
days before the cutoff and only on hours whose actuals were also available by then."

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
resolution; and the app is read-only by design, which keeps the pilot simple. Happy to take
questions on any part of the code."

## Pre-upload checklist
- [ ] Video unlisted, max 10:00 total; Part 1 and Part 2 each start with an overview <= 5:00
- [ ] Open the app, repo, and video links in an incognito window to verify access
- [ ] No personal identifiers in the public repo (brief requires an anonymous repo name)
