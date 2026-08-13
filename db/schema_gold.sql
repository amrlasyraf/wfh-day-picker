-- Gold: day-of-week ridership patterns, network-wide and per line.
-- "Busiest" day = best WFH candidate (avoiding it means avoiding the network's
-- heaviest crowding on the days you do commute). Median is used as the primary
-- ranking signal since public holidays create low outliers that skew the mean
-- down for whichever weekday they happen to fall on in a given year.

CREATE OR REPLACE TABLE gold.network_daily_totals AS
SELECT date, weekday_name, weekday_num, sum(ridership) AS daily_ridership
FROM silver.fact_station_departures_daily
GROUP BY date, weekday_name, weekday_num;

CREATE OR REPLACE TABLE gold.weekday_summary AS
SELECT
    weekday_num,
    weekday_name,
    round(avg(daily_ridership)) AS avg_ridership,
    round(median(daily_ridership)) AS median_ridership,
    min(daily_ridership) AS min_ridership,
    max(daily_ridership) AS max_ridership,
    count(*) AS n_days_observed,
    rank() OVER (ORDER BY median(daily_ridership) DESC) AS busiest_rank
FROM gold.network_daily_totals
GROUP BY weekday_num, weekday_name;

CREATE OR REPLACE TABLE gold.line_daily_totals AS
SELECT date, weekday_name, weekday_num, line_name, mode, sum(ridership) AS daily_ridership
FROM silver.fact_station_departures_daily
GROUP BY date, weekday_name, weekday_num, line_name, mode;

CREATE OR REPLACE TABLE gold.weekday_summary_by_line AS
SELECT
    line_name,
    mode,
    weekday_num,
    weekday_name,
    round(avg(daily_ridership)) AS avg_ridership,
    round(median(daily_ridership)) AS median_ridership,
    count(*) AS n_days_observed,
    rank() OVER (PARTITION BY line_name ORDER BY median(daily_ridership) DESC) AS busiest_rank
FROM gold.line_daily_totals
GROUP BY line_name, mode, weekday_num, weekday_name;
