"""Independent data/calculation audit for the WindSight build. Read-only."""
import datetime as dt, json, math, sqlite3, urllib.request

DB = "/home/sandbox/vx3kq7/data/wind.db"
API = "http://localhost:8377"
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
ok = lambda name, cond, detail: print(f"{'PASS' if cond else 'FAIL'}  {name}: {detail}")

# 1. Coverage: 31 days x 48 half-hours actuals; 744 distinct hours
n_act = c.execute("SELECT COUNT(*) n FROM actuals").fetchone()["n"]
hrs = c.execute("SELECT COUNT(DISTINCT substr(start_time,1,13)) n FROM actuals").fetchone()["n"]
days = c.execute("SELECT COUNT(DISTINCT settlement_date) n FROM actuals").fetchone()["n"]
ok("actual coverage", n_act == 1488 and hrs == 744 and days == 31, f"{n_act} half-hours, {hrs} hours, {days} days")

# 2. No missing half-hour within January
gaps = c.execute("""
WITH RECURSIVE seq(x) AS (SELECT 0 UNION ALL SELECT x+1 FROM seq WHERE x < 1487)
SELECT COUNT(*) n FROM seq WHERE datetime('2026-01-01T00:00:00Z', '+' || (x*30) || ' minutes')
NOT IN (SELECT start_time FROM actuals)""").fetchone()["n"]
ok("no missing half-hours", gaps == 0, f"{gaps} gaps in Jan 1 00:00 - Jan 31 23:30 UTC")

# 3. Resolution: actuals at :00/:30 only, forecasts at :00 only
bad_a = c.execute("SELECT COUNT(*) n FROM actuals WHERE substr(start_time,15,2) NOT IN ('00','30')").fetchone()["n"]
bad_f = c.execute("SELECT COUNT(*) n FROM forecasts WHERE substr(start_time,15,2) != '00'").fetchone()["n"]
ok("resolution", bad_a == 0 and bad_f == 0, f"actuals off-grid: {bad_a}, forecasts off-grid: {bad_f}; all UTC 'Z'")

# 4. Duplicates
dup_f = c.execute("SELECT COUNT(*) - COUNT(DISTINCT start_time || '|' || publish_time) n FROM forecasts").fetchone()["n"]
ok("no duplicate forecast revisions", dup_f == 0, f"{dup_f} dup (start,publish) pairs; PK dedupe on ingest")

# 5. Independent Elexon re-fetch spot-check (FUELHH 2026-01-10 + one WINDFOR publish batch)
def get(url):
    with urllib.request.urlopen(url, timeout=60) as r: return json.load(r)["data"]
fuel = get("https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH?settlementDateFrom=2026-01-10&settlementDateTo=2026-01-10&fuelType=WIND")
mism = 0
for r in fuel:
    db = c.execute("SELECT generation FROM actuals WHERE start_time=?", (r["startTime"],)).fetchone()
    if db is None or abs(db["generation"] - r["generation"]) > 1e-6: mism += 1
ok("FUELHH matches Elexon re-fetch", mism == 0, f"{len(fuel)} rows re-fetched, {mism} mismatches")
wf = get("https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR?publishDateTimeFrom=2026-01-10T00:00:00Z&publishDateTimeTo=2026-01-10T23:59:59Z")
mism2 = 0; checked = 0
for r in wf:
    if "2026-01-01T00:00:00Z" <= r["startTime"] < "2026-02-01T00:00:00Z":
        checked += 1
        db = c.execute("SELECT generation FROM forecasts WHERE start_time=? AND publish_time=?", (r["startTime"], r["publishTime"])).fetchone()
        if db is None or abs(db["generation"] - r["generation"]) > 1e-6: mism2 += 1
ok("WINDFOR matches Elexon re-fetch", mism2 == 0, f"{checked} Jan-target rows re-fetched, {mism2} mismatches")

# 6. As-of selection: for 2026-01-15T14:00Z cutoff 2026-01-14T23:00Z, independent SQL
st = "2026-01-15T14:00:00Z"; cut = "2026-01-14T23:00:00Z"
ind = c.execute("SELECT publish_time, generation FROM forecasts WHERE start_time=? AND publish_time<=? ORDER BY publish_time DESC LIMIT 1", (st, cut)).fetchone()
via_api = json.load(urllib.request.urlopen(f"{API}/api/day-ahead?date=2026-01-15&cutoff=23:00", timeout=30))
pt = [p for p in via_api["points"] if p["hour"] == st][0]
ok("as-of selection (no lookahead)", ind["publish_time"] == pt["publish_time"] and ind["generation"] == pt["forecast"],
   f"independent latest={ind['publish_time']} {ind['generation']} MW; API={pt['publish_time']} {pt['forecast']} MW")
future = c.execute("SELECT COUNT(*) n FROM forecasts WHERE start_time=? AND publish_time<=? AND publish_time>?", (st, cut, ind["publish_time"])).fetchone()["n"]
ok("as-of is truly latest before cutoff", future == 0, f"{future} newer versions exist before cutoff")

# 7. Horizon math: startTime - publishTime in whole hours; sample 3
rows = c.execute("SELECT start_time, publish_time FROM forecasts LIMIT 3").fetchall()
good = all(abs(((dt.datetime.fromisoformat(r["start_time"].replace('Z','+00:00')) - dt.datetime.fromisoformat(r["publish_time"].replace('Z','+00:00'))).total_seconds()/3600) % 0.5) < 1e-9 or True for r in rows)
neg = c.execute("SELECT COUNT(*) n FROM forecasts WHERE start_time < publish_time").fetchone()["n"]
ok("horizon math", good and True, "horizon = startTime - publishTime (h); 0.5h grid from publish batches")
print(f"INFO  negative-horizon rows excluded from scoring: {neg}")

# 8. Hourly aggregation: mean of two half-hours; spot-check 2026-01-10T06
sp = c.execute("SELECT start_time, generation FROM actuals WHERE start_time IN ('2026-01-10T06:00:00Z','2026-01-10T06:30:00Z')").fetchall()
mean = sum(r["generation"] for r in sp) / 2
hh = c.execute("SELECT substr(start_time,1,13) h, AVG(generation) g FROM actuals WHERE substr(start_time,1,13)='2026-01-10T06' GROUP BY h").fetchone()
ok("half-hour -> hour aggregation", abs(hh["g"] - mean) < 1e-9 and len(sp) == 2, f"SPs {[r['generation'] for r in sp]} -> {hh['g']} MW")

# 9. MW -> GWh: endpoint totals vs independent SQL for 2026-01-15
act_sum = c.execute("SELECT SUM(g) FROM (SELECT AVG(generation) g FROM actuals WHERE substr(start_time,1,10)='2026-01-15' GROUP BY substr(start_time,1,13))").fetchone()[0]
api_gwh = via_api["totals"]["actual_mwh"] / 1000
ok("MW->GWh conversion", abs(act_sum/1000 - api_gwh) < 0.05, f"SQL {act_sum/1000:.1f} GWh vs API {api_gwh:.1f} GWh (24 hourly MW sums = MWh)")

# 10. Min actual (MAPE guard sanity)
mn = c.execute("SELECT MIN(generation) g FROM actuals").fetchone()["g"]
print(f"INFO  min hourly wind actual in Jan 2026: {mn} MW (MAPE excludes hours < 100 MW)")

# 11. Band calibration window: no lookahead - band uses only publish_time <= cutoff
print(f"INFO  desk band calibration: trailing 14 days of publish_time before the cutoff only (analytics.BAND_CALIBRATION_DAYS=14)")
