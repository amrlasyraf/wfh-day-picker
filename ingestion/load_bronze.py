"""Bronze: load a landed yearly parquet file into DuckDB, replacing that year's rows."""
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import RIDERSHIP_BRONZE_DIR, RIDERSHIP_YEARS
from db import connect

SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "db" / "schema_bronze.sql"


def load(con, year: int):
    parquet_path = RIDERSHIP_BRONZE_DIR / f"{year}.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"No bronze parquet for {year} at {parquet_path}. Run fetch_ridership.py first.")

    con.execute(SCHEMA_SQL_PATH.read_text())
    con.execute("DELETE FROM bronze.ridership_od WHERE _year = ?", [year])
    con.execute(
        """
        INSERT INTO bronze.ridership_od
        SELECT origin, destination, date, ridership, ? AS _year, ? AS _loaded_at
        FROM read_parquet(?)
        """,
        [year, datetime.now(timezone.utc), str(parquet_path)],
    )
    n = con.execute("SELECT count(*) FROM bronze.ridership_od WHERE _year = ?", [year]).fetchone()[0]
    print(f"[bronze] {year}: loaded {n:,} rows")


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or RIDERSHIP_YEARS
    con = connect()
    for y in years:
        load(con, y)
    con.close()
