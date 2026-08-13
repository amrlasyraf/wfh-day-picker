"""Run the full bronze -> silver -> gold pipeline for rail ridership OD data."""
import sys

import build_gold
import fetch_ridership
import load_bronze
import transform_silver
from config import RIDERSHIP_YEARS
from db import connect


def main(years):
    con = connect()
    for year in years:
        print(f"\n=== {year} ===")
        fetch_ridership.fetch(year)
        load_bronze.load(con, year)
    transform_silver.transform(con)
    build_gold.build(con)
    con.close()


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or RIDERSHIP_YEARS
    main(years)
