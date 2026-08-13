from pathlib import Path

from db import connect

SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "db" / "schema_gold.sql"


def build(con):
    for stmt in SCHEMA_SQL_PATH.read_text().split(";\n\n"):
        stmt = stmt.strip()
        if stmt:
            con.execute(stmt)
    summary = con.execute(
        "SELECT weekday_name, median_ridership, busiest_rank FROM gold.weekday_summary ORDER BY weekday_num"
    ).fetchall()
    print("[gold] weekday_summary:")
    for row in summary:
        print(f"         {row[0]:<10} median={row[1]:>10,.0f}  busiest_rank={row[2]}")


if __name__ == "__main__":
    con = connect()
    build(con)
    con.close()
