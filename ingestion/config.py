from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
RIDERSHIP_BRONZE_DIR = BRONZE_DIR / "ridership_od_rapidrail"
WAREHOUSE_PATH = DATA_DIR / "warehouse.duckdb"

RIDERSHIP_URL_TEMPLATE = "https://storage.data.gov.my/transportation/rail/rapidrail_{year}_daily.parquet"
RIDERSHIP_YEARS = [2023, 2024, 2025, 2026]

# Station-code prefix -> (line name, mode). Derived from the ridership dataset's
# own station codes (distinct from the GTFS static feed's route_id scheme).
# Shah Alam Line has no ridership data in this dataset yet.
LINE_BY_PREFIX = {
    "AG": ("LRT Ampang Line", "LRT"),
    "KJ": ("LRT Kelana Jaya Line", "LRT"),
    "SP": ("LRT Sri Petaling Line", "LRT"),
    "KG": ("MRT Kajang Line", "MRT"),
    "PYL": ("MRT Putrajaya Line", "MRT"),
    "MR": ("KL Monorail Line", "Monorail"),
}
INCLUDED_MODES = ["LRT", "MRT"]  # Monorail excluded per project scope
