from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "Prepared" / "car_data_clean.csv"

NUMERIC_FEATURES = [
    "price_usd",
    "year",
    "mileage",
    "engine_volume_l",
    "owners_count",
]
