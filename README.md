# WFH Day Picker

Which day of the week should you work from home to avoid the worst Klang Valley
LRT/MRT crowding? Built on 3+ years of official daily ridership data from
`data.gov.my`. Sibling project to [`kl-rail-pulse`](../kl-rail-pulse), same
medallion pipeline shape, separate repo.

## Data source

`ridership_od_rapidrail_daily` — daily origin-destination trip counts across the
entire Rapid Rail network, from anonymized tap-in/tap-out records.

- **Coverage:** 2023-04-01 to present, updated daily
- **Download:** `https://storage.data.gov.my/transportation/rail/rapidrail_{year}_daily.parquet`
- **Columns:** `origin`, `destination`, `date`, `ridership` (trip count, not unique riders)
- **Granularity ceiling:** daily × station-pair — **no time-of-day breakdown** for
  rail (KTM Komuter/ETS/Intercity have hourly OD, rail does not)
- **Wildcard rows:** `origin = "A0: All Stations"` (or same on `destination`) are
  the dataset's own pre-aggregated daily totals per station — used directly for
  network-wide totals instead of summing every OD pair by hand
- **Scope:** LRT (Ampang, Kelana Jaya, Sri Petaling) + MRT (Kajang, Putrajaya)
  only, per project scope. Monorail is present in the source data but excluded.
  Shah Alam LRT has no ridership data in this dataset yet.

## Architecture — medallion (bronze / silver / gold)

Same shape as `kl-rail-pulse`: one DuckDB file (`data/warehouse.duckdb`), three
schemas.

```
data.gov.my (yearly ridership parquet, 2023-2026)
        │  ingestion/fetch_ridership.py
        ▼
  data/bronze/ridership_od_rapidrail/<year>.parquet   (raw landing, immutable)
        │  ingestion/load_bronze.py
        ▼
  bronze.ridership_od                                  (~20.6M rows, replaced per year)
        │  ingestion/transform_silver.py
        ▼
  silver.dim_stations           station code -> name, line, mode (LRT/MRT only)
  silver.fact_od_daily          real station-to-station daily trips (~17M rows)
  silver.fact_station_departures_daily   per-station daily boardings (from the
                                          dataset's own "All Stations" wildcard)
        │  ingestion/build_gold.py
        ▼
  gold.weekday_summary            network-wide median/avg/stddev ridership by
                                   weekday, ranked busiest-to-quietest
  gold.weekday_summary_by_line    same, split per line
  gold.weekday_summary_by_zone    same, split CBD-core vs residential/suburban
                                   (see caveat below)
        │
        ▼
  api/main.py (FastAPI)  →  web/static/index.html
```

**Why median, not mean:** public holidays create low-ridership outliers that land
on whatever weekday they happen to fall on in a given year. Median is robust to
that; mean is shown alongside for reference but doesn't drive the recommendation.

**Recommendation logic:** the busiest weekday (Mon-Fri) by median network-wide
daily boardings is the suggested WFH day — staying home that day avoids the
network's heaviest crowding on the days you do commute. The main chart also
shows each weekday's min-max range (a whisker), since the "busiest" day by
median can be a thin margin over its neighbors — check the range before
treating day-of-week rank as a hard signal.

**CBD-core vs residential/suburban split:** the network-wide total blends real
commute trips with everything else (leisure, errands, non-commute travel),
which can hide a weekday's true commute-driven shape. `gold.weekday_summary_by_zone`
compares a small **hand-picked** set of well-known CBD-core stations (KLCC, KL
Sentral, Pasar Seni, Masjid Jamek, Bukit Bintang, Ampang Park, Dang Wangi,
Merdeka, TRX) against outer residential/suburban termini (Ampang, Gombak,
Kajang, Kwasa Damansara, Puchong Prima, Putra Heights) — see
`ingestion/config.py`. This is **not** derived from any official land-use or
employment dataset, just station identity; treat it as illustrative, not
authoritative. It does surface a real split: across the full history, **CBD-core
stations peak on Friday** while **residential/suburban stations peak on
Wednesday** — the network-wide Wednesday recommendation is an average of two
different underlying shapes.

## Running locally

```bash
pip install -r requirements.txt

# Bronze -> silver -> gold (re-run to pull the latest year's data)
python ingestion/run_pipeline.py

# API + static frontend
python -m uvicorn api.main:app --reload --port 8001
# open http://127.0.0.1:8001/
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | liveness + date range covered |
| `GET /api/weekday-summary` | network-wide weekday ridership + recommended WFH day |
| `GET /api/weekday-summary/by-line?line_name=` | same, filtered to one line |
| `GET /api/weekday-summary/by-zone` | CBD-core vs residential/suburban weekday comparison |
| `GET /api/lines` | LRT/MRT lines present in the data |
| `GET /api/stations` | all LRT/MRT stations (code, name, line, mode) |
| `GET /api/commute-summary?origin_code=&destination_code=` | weekday pattern + recommendation for one specific station pair |

## Known limitations

- **No time-of-day granularity for rail** — this only tells you which *day* is
  busiest, not which *hour*. If you want hour-level crowding, that data only
  exists for KTM Komuter/ETS/Intercity, not LRT/MRT.
- **Public holidays aren't explicitly excluded**, only dampened via median vs
  mean. A future pass could join against a Malaysia public holiday calendar to
  exclude them outright.
- **Ridership = trips, not unique passengers or vehicle occupancy.** It's a good
  proxy for "how busy was the network that day," not a literal crowding/occupancy
  number.
