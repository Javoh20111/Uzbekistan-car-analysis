import pandas as pd
import duckdb
import os
import tomllib
from pathlib import Path
from sqlalchemy import create_engine
from urllib.parse import quote_plus

DUCKDB_PATH = "cars.duckdb"
SECRETS_PATH = Path(".streamlit/secrets.toml")

TABLES = [
    "brands",
    "currencies",
    "conditions",
    "colors",
    "transmissions",
    "fuel_types",
    "regions",
    "districts",
    "additional_options",
    "sale_options",
    "cars",
    "car_listings",
    "listing_sale_options",
    "listing_additional_options",
]


def get_postgres_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    with SECRETS_PATH.open("rb") as file:
        secrets = tomllib.load(file)

    pg = secrets["connections"]["postgresql"]
    username = quote_plus(str(pg["username"]))
    password = quote_plus(str(pg["password"]))
    host = pg["host"]
    port = pg["port"]
    database = pg["database"]

    return f"postgresql://{username}:{password}@{host}:{port}/{database}"


def main():
    pg_engine = create_engine(get_postgres_url())
    duck = duckdb.connect(DUCKDB_PATH)

    try:
        for table in TABLES:
            df = pd.read_sql(f"SELECT * FROM {table}", pg_engine)
            duck.register("source_df", df)
            duck.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM source_df")
            duck.unregister("source_df")
            print(f"Copied {len(df):,} rows into {table}")
    finally:
        duck.close()
        pg_engine.dispose()

    print(f"Created {DUCKDB_PATH}")


if __name__ == "__main__":
    main()
