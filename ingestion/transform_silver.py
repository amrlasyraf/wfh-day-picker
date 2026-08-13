"""Silver: split bronze OD rows into real OD pairs vs. pre-aggregated station daily
totals (the dataset's "A0: All Stations" wildcard rows), parse each station's line
from its code prefix, and keep only LRT/MRT stations (Monorail excluded per scope).
"""
from config import INCLUDED_MODES, LINE_BY_PREFIX
from db import connect

PREFIX_EXPR = "regexp_extract(code, '^([A-Za-z]+)', 1)"


def _line_case_expr(prefix_col: str) -> str:
    cases = " ".join(
        f"WHEN {prefix_col} = '{prefix}' THEN '{mode}'" for prefix, (_, mode) in LINE_BY_PREFIX.items()
    )
    return f"CASE {cases} ELSE NULL END"


def _name_case_expr(prefix_col: str) -> str:
    cases = " ".join(
        f"WHEN {prefix_col} = '{prefix}' THEN '{name}'" for prefix, (name, _) in LINE_BY_PREFIX.items()
    )
    return f"CASE {cases} ELSE NULL END"


def transform(con):
    included = ", ".join(f"'{m}'" for m in INCLUDED_MODES)

    # dim_stations: every distinct real (non-wildcard) station code seen, with parsed line/mode.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE silver.dim_stations AS
        WITH codes AS (
            SELECT DISTINCT split_part(origin, ':', 1) AS code, trim(split_part(origin, ':', 2)) AS name
            FROM bronze.ridership_od WHERE origin NOT LIKE 'A0%'
            UNION
            SELECT DISTINCT split_part(destination, ':', 1), trim(split_part(destination, ':', 2))
            FROM bronze.ridership_od WHERE destination NOT LIKE 'A0%'
        ),
        parsed AS (
            SELECT code, name, {PREFIX_EXPR} AS prefix
            FROM codes
        )
        SELECT code, name, prefix,
               {_line_case_expr('prefix')} AS mode,
               {_name_case_expr('prefix')} AS line_name
        FROM parsed
        WHERE {_line_case_expr('prefix')} IN ({included})
        """
    )

    # fact_od_daily: real station-to-station trips, both ends LRT/MRT.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE silver.fact_od_daily AS
        SELECT
            r.date,
            dayname(r.date) AS weekday_name,
            isodow(r.date) AS weekday_num,
            os.code AS origin_code, os.name AS origin_name, os.line_name AS origin_line,
            ds.code AS destination_code, ds.name AS destination_name, ds.line_name AS destination_line,
            r.ridership
        FROM bronze.ridership_od r
        JOIN silver.dim_stations os ON os.code = split_part(r.origin, ':', 1)
        JOIN silver.dim_stations ds ON ds.code = split_part(r.destination, ':', 1)
        WHERE r.origin NOT LIKE 'A0%' AND r.destination NOT LIKE 'A0%'
        """
    )

    # fact_station_departures_daily: total daily boardings per station (destination = wildcard).
    con.execute(
        f"""
        CREATE OR REPLACE TABLE silver.fact_station_departures_daily AS
        SELECT
            r.date,
            dayname(r.date) AS weekday_name,
            isodow(r.date) AS weekday_num,
            s.code AS station_code, s.name AS station_name, s.line_name, s.mode,
            r.ridership
        FROM bronze.ridership_od r
        JOIN silver.dim_stations s ON s.code = split_part(r.origin, ':', 1)
        WHERE r.destination LIKE 'A0%' AND r.origin NOT LIKE 'A0%'
        """
    )

    n_stations = con.execute("SELECT count(*) FROM silver.dim_stations").fetchone()[0]
    n_od = con.execute("SELECT count(*) FROM silver.fact_od_daily").fetchone()[0]
    n_dep = con.execute("SELECT count(*) FROM silver.fact_station_departures_daily").fetchone()[0]
    print(f"[silver] dim_stations={n_stations}, fact_od_daily={n_od:,}, fact_station_departures_daily={n_dep:,}")


if __name__ == "__main__":
    con = connect()
    transform(con)
    con.close()
