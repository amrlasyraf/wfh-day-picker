"""REST API over the gold/silver layers: network-wide and per-commute-pair
day-of-week ridership patterns, to help pick the best weekly WFH day.
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestion"))
from db import connect  # noqa: E402

app = FastAPI(title="WFH Day Picker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEEKDAY_ORDER = "CASE weekday_name WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END"


def get_con():
    return connect()


@app.get("/api/health")
def health():
    con = get_con()
    n_days = con.execute("SELECT count(*) FROM gold.network_daily_totals").fetchone()[0]
    date_range = con.execute("SELECT min(date), max(date) FROM gold.network_daily_totals").fetchone()
    con.close()
    return {"status": "ok", "days_observed": n_days, "date_range": [str(d) for d in date_range]}


@app.get("/api/weekday-summary")
def weekday_summary():
    con = get_con()
    rows = con.execute(
        """
        SELECT weekday_name, avg_ridership, median_ridership, min_ridership, max_ridership,
               n_days_observed, busiest_rank
        FROM gold.weekday_summary
        ORDER BY weekday_num
        """
    ).fetchall()
    cols = [d[0] for d in con.description]
    weekdays_only = con.execute(
        """
        SELECT weekday_name, median_ridership
        FROM gold.weekday_summary
        WHERE weekday_num BETWEEN 1 AND 5
        ORDER BY median_ridership DESC LIMIT 1
        """
    ).fetchone()
    con.close()
    return {
        "weekdays": [dict(zip(cols, r)) for r in rows],
        "recommended_wfh_day": weekdays_only[0],
        "note": "Recommendation = busiest weekday by median network-wide daily boardings across LRT+MRT (2023-04 to present). Median is used instead of mean so public holidays don't skew a weekday's typical pattern.",
    }


@app.get("/api/lines")
def lines():
    con = get_con()
    rows = con.execute(
        "SELECT DISTINCT line_name, mode FROM silver.dim_stations ORDER BY mode, line_name"
    ).fetchall()
    con.close()
    return [{"line_name": r[0], "mode": r[1]} for r in rows]


@app.get("/api/weekday-summary/by-line")
def weekday_summary_by_line(line_name: str | None = None):
    con = get_con()
    if line_name:
        rows = con.execute(
            """
            SELECT line_name, mode, weekday_name, avg_ridership, median_ridership, busiest_rank
            FROM gold.weekday_summary_by_line
            WHERE line_name = ?
            ORDER BY weekday_num
            """,
            [line_name],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT line_name, mode, weekday_name, avg_ridership, median_ridership, busiest_rank
            FROM gold.weekday_summary_by_line
            ORDER BY line_name, weekday_num
            """
        ).fetchall()
    cols = [d[0] for d in con.description]
    con.close()
    return [dict(zip(cols, r)) for r in rows]


@app.get("/api/stations")
def stations():
    con = get_con()
    rows = con.execute(
        "SELECT code, name, line_name, mode FROM silver.dim_stations ORDER BY name"
    ).fetchall()
    cols = [d[0] for d in con.description]
    con.close()
    return [dict(zip(cols, r)) for r in rows]


@app.get("/api/commute-summary")
def commute_summary(origin_code: str, destination_code: str):
    con = get_con()
    rows = con.execute(
        f"""
        SELECT weekday_name,
               round(avg(ridership)) AS avg_ridership,
               round(median(ridership)) AS median_ridership,
               count(*) AS n_days_observed
        FROM silver.fact_od_daily
        WHERE origin_code = ? AND destination_code = ?
        GROUP BY weekday_name
        ORDER BY {WEEKDAY_ORDER}
        """,
        [origin_code, destination_code],
    ).fetchall()
    cols = [d[0] for d in con.description]
    con.close()

    weekdays_only = [r for r in rows if r[0] not in ("Saturday", "Sunday")]
    recommended = max(weekdays_only, key=lambda r: r[2])[0] if weekdays_only else None

    return {
        "origin_code": origin_code,
        "destination_code": destination_code,
        "weekdays": [dict(zip(cols, r)) for r in rows],
        "recommended_wfh_day": recommended,
    }


static_dir = Path(__file__).resolve().parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
