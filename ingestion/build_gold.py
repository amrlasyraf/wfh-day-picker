from pathlib import Path

from config import CBD_CORE_CODES, RESIDENTIAL_SUBURBAN_CODES
from db import connect

SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "db" / "schema_gold.sql"


def _build_zone_summary(con):
    """Curated CBD-core vs residential/suburban station comparison (see config.py
    for the caveat: these lists are hand-picked by station identity, not derived
    from any land-use dataset).
    """
    cbd_list = ", ".join(f"'{c}'" for c in CBD_CORE_CODES)
    residential_list = ", ".join(f"'{c}'" for c in RESIDENTIAL_SUBURBAN_CODES)

    con.execute(
        f"""
        CREATE OR REPLACE TABLE gold.zone_daily_totals AS
        SELECT
            date, weekday_name, weekday_num,
            CASE WHEN station_code IN ({cbd_list}) THEN 'CBD core'
                 WHEN station_code IN ({residential_list}) THEN 'Residential/suburban'
            END AS zone,
            sum(ridership) AS daily_ridership
        FROM silver.fact_station_departures_daily
        WHERE station_code IN ({cbd_list}, {residential_list})
        GROUP BY date, weekday_name, weekday_num, zone
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold.weekday_summary_by_zone AS
        SELECT
            zone,
            weekday_num,
            weekday_name,
            round(avg(daily_ridership)) AS avg_ridership,
            round(median(daily_ridership)) AS median_ridership,
            round(100.0 * (max(daily_ridership) - min(daily_ridership)) / avg(daily_ridership), 1) AS range_pct_of_avg,
            count(*) AS n_days_observed,
            rank() OVER (PARTITION BY zone ORDER BY median(daily_ridership) DESC) AS busiest_rank
        FROM gold.zone_daily_totals
        GROUP BY zone, weekday_num, weekday_name
        """
    )


def build(con):
    for stmt in SCHEMA_SQL_PATH.read_text().split(";\n\n"):
        stmt = stmt.strip()
        if stmt:
            con.execute(stmt)
    _build_zone_summary(con)

    summary = con.execute(
        "SELECT weekday_name, median_ridership, busiest_rank FROM gold.weekday_summary ORDER BY weekday_num"
    ).fetchall()
    print("[gold] weekday_summary:")
    for row in summary:
        print(f"         {row[0]:<10} median={row[1]:>10,.0f}  busiest_rank={row[2]}")

    zone_summary = con.execute(
        "SELECT zone, weekday_name, median_ridership FROM gold.weekday_summary_by_zone ORDER BY zone, weekday_num"
    ).fetchall()
    print("[gold] weekday_summary_by_zone:")
    for row in zone_summary:
        print(f"         {row[0]:<22} {row[1]:<10} median={row[2]:>8,.0f}")


if __name__ == "__main__":
    con = connect()
    build(con)
    con.close()
