"""
db_loader.py — Database Loader for the Car ETL Pipeline
---------------------------------------------------------
Loads a cleaned car DataFrame into the PostgreSQL relational schema defined in
sql/01_create_tables.sql.

Key design decisions
--------------------
* Lookup tables (brands, currencies, etc.) are synced before the fact tables.
  Any NEW value found in the daily batch gets inserted; existing values reuse
  their existing primary-key IDs.
* `cars` and `car_listings` use ON CONFLICT DO NOTHING so re-runs are safe.
* Bridge tables (listing_sale_options, listing_additional_options) are also
  upserted safely.

Usage
-----
    from pipeline.db_loader import load_to_db
    load_to_db(df, db_url="postgresql://postgres:8228@localhost:5432/cars_db")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger("etl.db_loader")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_lookup(engine, table: str, id_col: str, name_col: str, values: list) -> dict:
    """
    Ensure every value in `values` has a row in `table`.
    Returns a {value: id} mapping for all known values.

    Strategy: batch-insert ALL missing values with ON CONFLICT DO NOTHING,
    then re-read the full table.  This avoids any issue with RETURNING vs
    sequence mismatches and is safe to re-run.
    """
    if not values:
        return {}

    clean_values = list(dict.fromkeys(
        v for v in values if v is not None and str(v).strip() != ""
    ))

    with engine.connect() as conn:
        # Load existing rows first
        existing = pd.read_sql(
            f"SELECT {id_col}, {name_col} FROM {table}", conn
        )
        lookup = dict(zip(existing[name_col], existing[id_col]))

        # Find which values are truly new
        missing = [v for v in clean_values if v not in lookup]

        if missing:
            # Insert all missing values in a single batch statement.
            # ON CONFLICT DO NOTHING means already-existing names are silently skipped.
            placeholders = ", ".join(f"(:v{i})" for i in range(len(missing)))
            params       = {f"v{i}": v for i, v in enumerate(missing)}
            conn.execute(
                text(f"INSERT INTO {table} ({name_col}) VALUES {placeholders} ON CONFLICT ({name_col}) DO NOTHING"),
                params
            )
            conn.commit()

        # Re-read the full table to get all IDs (including newly inserted ones)
        existing = pd.read_sql(
            f"SELECT {id_col}, {name_col} FROM {table}", conn
        )
        lookup = dict(zip(existing[name_col], existing[id_col]))

    return lookup


def _nan_to_none(val):
    """Convert numpy NaN / pandas NA to Python None for SQL insertion."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _count_rows(conn, table: str) -> int:
    """Return row count for a known project table."""
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_to_db(df: pd.DataFrame, db_url: Optional[str] = None) -> int:
    """
    Load cleaned DataFrame into PostgreSQL.

    Parameters
    ----------
    df      : Cleaned DataFrame (output of the transformation pipeline).
    db_url  : SQLAlchemy connection string.  Falls back to DATABASE_URL env var,
              then to the project default.

    Returns
    -------
    int     : Number of rows successfully inserted / upserted.
    """
    if db_url is None:
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:8228@localhost:5432/cars_db"
        )

    logger.info(f"Connecting to database: {db_url.split('@')[-1]}")  # hide credentials in log
    engine = create_engine(db_url)

    # ── 1. Sync lookup tables ─────────────────────────────────────────────────
    logger.info("Syncing lookup tables …")

    def unique_vals(col):
        if col not in df.columns:
            return []
        return [v for v in df[col].dropna().unique() if str(v).strip() != ""]

    brand_map    = _get_or_create_lookup(engine, "brands",        "brand_id",       "brand_name",       unique_vals("brand"))
    currency_map = _get_or_create_lookup(engine, "currencies",    "currency_id",    "currency_name",    unique_vals("currency"))
    condition_map= _get_or_create_lookup(engine, "conditions",    "condition_id",   "condition_name",   unique_vals("condition"))
    color_map    = _get_or_create_lookup(engine, "colors",        "color_id",       "color_name",       unique_vals("color"))
    trans_map    = _get_or_create_lookup(engine, "transmissions", "transmission_id","transmission_name",unique_vals("transmission"))
    fuel_map     = _get_or_create_lookup(engine, "fuel_types",    "fuel_type_id",   "fuel_type_name",   unique_vals("fuel_type"))
    region_map   = _get_or_create_lookup(engine, "regions",       "region_id",      "region_name",      unique_vals("region"))
    district_map = _get_or_create_lookup(engine, "districts",     "district_id",    "district_name",    unique_vals("district"))

    # Collect all sale_type tokens from all rows (they can be comma-separated lists)
    all_sale_types = []
    if "sale_type" in df.columns:
        for val in df["sale_type"].dropna():
            if isinstance(val, list):
                all_sale_types.extend([v.strip() for v in val if v and v.strip()])
            else:
                all_sale_types.extend([v.strip() for v in str(val).split(",") if v.strip()])
    all_sale_types = list(dict.fromkeys(all_sale_types))

    all_add_opts = []
    if "additional_options" in df.columns:
        for val in df["additional_options"].dropna():
            if isinstance(val, list):
                all_add_opts.extend([v.strip() for v in val if v and v.strip()])
            else:
                all_add_opts.extend([v.strip() for v in str(val).split(",") if v.strip()])
    all_add_opts = list(dict.fromkeys(all_add_opts))

    sale_map  = _get_or_create_lookup(engine, "sale_options",         "option_id",           "sale_type",             all_sale_types)
    addopt_map= _get_or_create_lookup(engine, "additional_options",   "additional_option_id","additional_option_name", all_add_opts)

    logger.info("Lookup tables synced.")

    # ── 2. Insert fact tables row by row ─────────────────────────────────────
    rows_seen         = 0
    cars_inserted     = 0
    listings_inserted = 0
    duplicate_urls    = 0
    skipped           = 0
    bridge_rows       = 0

    total_cars = 0
    total_listings = 0

    with engine.connect() as conn:
        for _, row in df.iterrows():
            rows_seen += 1
            url = _nan_to_none(row.get("url"))
            if not url:
                skipped += 1
                continue

            # ── cars table ────────────────────────────────────────────────────
            brand_name = _nan_to_none(row.get("brand"))
            brand_id   = brand_map.get(brand_name) if brand_name else None

            year_val = _nan_to_none(row.get("year"))
            try:
                year_val = int(year_val) if year_val is not None else None
            except (ValueError, TypeError):
                year_val = None

            car_result = conn.execute(
                text("""
                    INSERT INTO cars (url, brand_id, model_raw, model_clean, car_name,
                                     year, year_valid, engine_volume_raw, engine_volume_l)
                    VALUES (:url, :brand_id, :model_raw, :model_clean, :car_name,
                            :year, :year_valid, :engine_volume_raw, :engine_volume_l)
                    ON CONFLICT (url) DO NOTHING
                """),
                {
                    "url":              url,
                    "brand_id":         brand_id,
                    "model_raw":        _nan_to_none(row.get("model_raw")),
                    "model_clean":      _nan_to_none(row.get("model_clean")),
                    "car_name":         _nan_to_none(row.get("car_name")),
                    "year":             year_val,
                    "year_valid":       _nan_to_none(row.get("year_valid")),
                    "engine_volume_raw":_nan_to_none(row.get("engine_volume_raw")),
                    "engine_volume_l":  _nan_to_none(row.get("engine_volume_l")),
                }
            )
            cars_inserted += car_result.rowcount or 0

            # ── car_listings table ────────────────────────────────────────────
            currency     = _nan_to_none(row.get("currency"))
            currency_id  = currency_map.get(currency) if currency else None

            condition    = _nan_to_none(row.get("condition"))
            condition_id = condition_map.get(condition) if condition else None

            color        = _nan_to_none(row.get("color"))
            color_id     = color_map.get(color) if color else None

            transmission  = _nan_to_none(row.get("transmission"))
            trans_id      = trans_map.get(transmission) if transmission else None

            fuel_type    = _nan_to_none(row.get("fuel_type"))
            fuel_id      = fuel_map.get(fuel_type) if fuel_type else None

            region       = _nan_to_none(row.get("region"))
            region_id    = region_map.get(region) if region else None

            district     = _nan_to_none(row.get("district"))
            district_id  = district_map.get(district) if district else None

            mileage      = _nan_to_none(row.get("mileage"))
            mileage_log  = _nan_to_none(row.get("mileage_log"))
            mileage_grp  = _nan_to_none(row.get("mileage_group"))
            if mileage_grp is not None:
                mileage_grp = str(mileage_grp)

            owners_count = _nan_to_none(row.get("owners_count"))
            try:
                owners_count = int(owners_count) if owners_count is not None else None
            except (ValueError, TypeError):
                owners_count = None

            price_raw    = _nan_to_none(row.get("price_raw"))
            try:
                price_raw = int(price_raw) if price_raw is not None else None
            except (ValueError, TypeError):
                price_raw = None

            price_usd    = _nan_to_none(row.get("price_usd"))
            is_outlier   = _nan_to_none(row.get("is_outlier"))

            listing_result = conn.execute(
                text("""
                    INSERT INTO car_listings
                        (url, description, price_raw, price_usd, is_outlier,
                         currency_id, condition_id, color_id, transmission_id,
                         fuel_type_id, region_id, district_id,
                         mileage, mileage_log, mileage_group,
                         owners_count, image_url)
                    VALUES
                        (:url, :description, :price_raw, :price_usd, :is_outlier,
                         :currency_id, :condition_id, :color_id, :transmission_id,
                         :fuel_type_id, :region_id, :district_id,
                         :mileage, :mileage_log, :mileage_group,
                         :owners_count, :image_url)
                    ON CONFLICT (url) DO NOTHING
                """),
                {
                    "url":            url,
                    "description":    _nan_to_none(row.get("description")),
                    "price_raw":      price_raw,
                    "price_usd":      price_usd,
                    "is_outlier":     bool(is_outlier) if is_outlier is not None else None,
                    "currency_id":    currency_id,
                    "condition_id":   condition_id,
                    "color_id":       color_id,
                    "transmission_id":trans_id,
                    "fuel_type_id":   fuel_id,
                    "region_id":      region_id,
                    "district_id":    district_id,
                    "mileage":        mileage,
                    "mileage_log":    mileage_log,
                    "mileage_group":  mileage_grp,
                    "owners_count":   owners_count,
                    "image_url":      _nan_to_none(row.get("image_url")),
                }
            )
            inserted_listing = listing_result.rowcount or 0
            listings_inserted += inserted_listing
            if inserted_listing == 0:
                duplicate_urls += 1

            # ── listing_sale_options bridge ───────────────────────────────────
            sale_type_val = row.get("sale_type")
            if sale_type_val is not None:
                if isinstance(sale_type_val, list):
                    tokens = [v.strip() for v in sale_type_val if v and v.strip()]
                else:
                    tokens = [v.strip() for v in str(sale_type_val).split(",") if v.strip()]
                for token in tokens:
                    opt_id = sale_map.get(token)
                    if opt_id:
                        bridge_result = conn.execute(
                            text("""
                                INSERT INTO listing_sale_options (url, option_id)
                                VALUES (:url, :option_id)
                                ON CONFLICT DO NOTHING
                            """),
                            {"url": url, "option_id": opt_id}
                        )
                        bridge_rows += bridge_result.rowcount or 0

            # ── listing_additional_options bridge ─────────────────────────────
            add_opts_val = row.get("additional_options")
            if add_opts_val is not None:
                if isinstance(add_opts_val, list):
                    tokens = [v.strip() for v in add_opts_val if v and v.strip()]
                else:
                    tokens = [v.strip() for v in str(add_opts_val).split(",") if v.strip()]
                for token in tokens:
                    opt_id = addopt_map.get(token)
                    if opt_id:
                        bridge_result = conn.execute(
                            text("""
                                INSERT INTO listing_additional_options (url, additional_option_id)
                                VALUES (:url, :additional_option_id)
                                ON CONFLICT DO NOTHING
                            """),
                            {"url": url, "additional_option_id": opt_id}
                        )
                        bridge_rows += bridge_result.rowcount or 0

        conn.commit()
        total_cars = _count_rows(conn, "cars")
        total_listings = _count_rows(conn, "car_listings")

    logger.info(
        f"DB load complete — rows seen: {rows_seen}, cars inserted: {cars_inserted}, "
        f"listings inserted: {listings_inserted}, duplicate listings: {duplicate_urls}, "
        f"bridge rows inserted: {bridge_rows}, skipped: {skipped}, "
        f"table totals: cars={total_cars}, listings={total_listings}"
    )
    return listings_inserted
