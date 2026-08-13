-- Bronze: raw ridership rows as landed (parquet source is already typed, so no
-- need to flatten to VARCHAR the way the CSV-sourced GTFS bronze layer does).
CREATE TABLE IF NOT EXISTS bronze.ridership_od (
    origin VARCHAR,
    destination VARCHAR,
    date DATE,
    ridership BIGINT,
    _year INTEGER,
    _loaded_at TIMESTAMP
);
