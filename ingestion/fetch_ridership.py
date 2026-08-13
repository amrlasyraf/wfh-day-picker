"""Bronze: download raw yearly ridership parquet files from data.gov.my, unmodified."""
import sys

import requests

from config import RIDERSHIP_BRONZE_DIR, RIDERSHIP_URL_TEMPLATE, RIDERSHIP_YEARS


def fetch(year: int):
    url = RIDERSHIP_URL_TEMPLATE.format(year=year)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    RIDERSHIP_BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RIDERSHIP_BRONZE_DIR / f"{year}.parquet"
    out_path.write_bytes(resp.content)
    print(f"[bronze] {year}: {len(resp.content):,} bytes -> {out_path}")
    return out_path


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or RIDERSHIP_YEARS
    for y in years:
        fetch(y)
