"""
orchestrator.py — Daily ETL Pipeline Orchestrator
--------------------------------------------------
Automates the full Extract → Transform → Load cycle for OLX.uz car listings.

Daily workflow
--------------
1. EXTRACT  — Run the OLX scraper and write a date-stamped CSV to data/raw/.
2. TRANSFORM — Clean the raw CSV using the transformation pipeline.
3. LOAD      — Upsert the cleaned rows into the local PostgreSQL database.
4. ARCHIVE   — Move the processed raw CSV to data/raw/explored/.

Usage
-----
    # Full daily run (from repo root)
    python pipeline/orchestrator.py

    # Quick smoke-test: scrape only 10 listings end-to-end
    python pipeline/orchestrator.py --test 10

    # Skip scraping, transform & load an existing raw file
    python pipeline/orchestrator.py --skip-scrape --raw-file data/raw/olx_car_data_2026-05-25.csv

    # Override database URL
    python pipeline/orchestrator.py --db-url postgresql://user:pass@host/db
"""

import argparse
import logging
import os
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# ── Ensure both pipeline/ and the repo root are on sys.path ──────────────────
PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT    = PIPELINE_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PIPELINE_DIR))

from transformation import (
    district_cleaner,
    duplicate_remover,
    engine_volume_cleaner,
    mileage_cleaner,
    model_cleaner,
    owners_count_cleaner,
    price_validatetor,
    seller_type_cleaner,
    year_cleaner,
)
from db_loader import load_to_db

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
def _setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("etl")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────────────────────────────────────
TRANSFORMATIONS = [
    duplicate_remover,
    model_cleaner,
    price_validatetor,
    mileage_cleaner,
    engine_volume_cleaner,
    owners_count_cleaner,
    seller_type_cleaner,
    year_cleaner,
    district_cleaner,
]


def step_extract(output_csv: Path, test_limit: int | None, logger: logging.Logger) -> Path:
    """Run the OLX scraper and save results to a date-stamped CSV."""
    # Import here so Selenium is only loaded when scraping is needed
    from scraper.olx_scraper import OlxScraper

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"[EXTRACT] Starting OLX scraper → {output_csv}")

    scraper = OlxScraper(output_file=str(output_csv))
    scraper.run(test_limit=test_limit)

    if not output_csv.exists() or output_csv.stat().st_size == 0:
        raise RuntimeError(f"Scraper finished but output file is empty or missing: {output_csv}")

    row_count = sum(1 for _ in open(output_csv, encoding="utf-8")) - 1  # subtract header
    logger.info(f"[EXTRACT] Done — {row_count} rows written to {output_csv}")
    return output_csv


def step_transform(raw_csv: Path, logger: logging.Logger) -> pd.DataFrame:
    """Load raw CSV and apply all cleaning transformations."""
    logger.info(f"[TRANSFORM] Loading raw data from {raw_csv}")
    df = pd.read_csv(raw_csv, low_memory=False)
    logger.info(f"[TRANSFORM] Raw shape: {df.shape}")

    for fn in TRANSFORMATIONS:
        separator = "-" * 40
        logger.info(f"\n{separator}\n[TRANSFORM] Running: {fn.__name__}\n{separator}")
        df = fn(df)

    logger.info(f"[TRANSFORM] Done — cleaned shape: {df.shape}")
    return df


def step_save_clean(df: pd.DataFrame, processed_dir: Path, today: str, logger: logging.Logger) -> Path:
    """Save cleaned DataFrame to data/Processed/YYYY-MM-DD/car_data_clean.csv."""
    out_dir = processed_dir / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "car_data_clean.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"[TRANSFORM] Cleaned data saved → {out_path}")
    return out_path


def step_load(df: pd.DataFrame, db_url: str, logger: logging.Logger) -> int:
    """Upsert cleaned data into PostgreSQL."""
    logger.info("[LOAD] Starting database insertion …")
    count = load_to_db(df, db_url=db_url)
    logger.info(f"[LOAD] Done — {count} listings processed.")
    return count


def step_archive(raw_csv: Path, explored_dir: Path, today: str, logger: logging.Logger):
    """Move the raw CSV to data/raw/explored/<date>/ after successful load."""
    dest_dir = explored_dir / today
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / raw_csv.name
    shutil.move(str(raw_csv), str(dest))
    logger.info(f"[ARCHIVE] Raw file moved → {dest}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Daily ETL pipeline — OLX.uz car listings → PostgreSQL"
    )
    parser.add_argument(
        "--test", type=int, default=None, metavar="N",
        help="Scrape only N listings (quick smoke-test mode)"
    )
    parser.add_argument(
        "--skip-scrape", action="store_true",
        help="Skip scraping and use an existing raw file (requires --raw-file)"
    )
    parser.add_argument(
        "--raw-file", type=str, default=None,
        help="Path to an existing raw CSV to transform & load (used with --skip-scrape)"
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="PostgreSQL connection string (overrides DATABASE_URL env var)"
    )
    parser.add_argument(
        "--no-load", action="store_true",
        help="Skip the database load step (transform only)"
    )
    parser.add_argument(
        "--no-archive", action="store_true",
        help="Skip archiving raw files after load"
    )
    args = parser.parse_args()

    # ── Resolve paths ─────────────────────────────────────────────────────────
    today        = date.today().isoformat()   # e.g. "2026-05-25"
    raw_dir      = REPO_ROOT / "data" / "raw"
    explored_dir = raw_dir / "explored"
    processed_dir= REPO_ROOT / "data" / "Processed"
    log_dir      = REPO_ROOT / "data" / "logs"

    raw_dir.mkdir(parents=True, exist_ok=True)
    explored_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / f"etl_{today}.log"
    logger   = _setup_logging(log_path)

    db_url = args.db_url or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:8228@localhost:5432/cars_db"
    )

    logger.info("=" * 60)
    logger.info(f"ETL Pipeline started — date: {today}")
    if args.test:
        logger.info(f"TEST MODE — limited to {args.test} scraped listings")
    logger.info("=" * 60)

    # ── Step 1: Extract ───────────────────────────────────────────────────────
    if args.skip_scrape:
        if not args.raw_file:
            logger.error("--skip-scrape requires --raw-file <path>")
            sys.exit(1)
        raw_csv = Path(args.raw_file).resolve()
        if not raw_csv.exists():
            logger.error(f"Raw file not found: {raw_csv}")
            sys.exit(1)
        logger.info(f"[EXTRACT] Skipped — using existing file: {raw_csv}")
    else:
        suffix   = f"_test" if args.test else ""
        raw_csv  = raw_dir / f"olx_car_data{suffix}_{today}.csv"
        try:
            step_extract(raw_csv, test_limit=args.test, logger=logger)
        except Exception as e:
            logger.error(f"[EXTRACT] FAILED: {e}", exc_info=True)
            sys.exit(1)

    # ── Step 2: Transform ─────────────────────────────────────────────────────
    try:
        df = step_transform(raw_csv, logger=logger)
    except Exception as e:
        logger.error(f"[TRANSFORM] FAILED: {e}", exc_info=True)
        sys.exit(1)

    # ── Step 2b: Save cleaned CSV ─────────────────────────────────────────────
    try:
        step_save_clean(df, processed_dir, today, logger=logger)
    except Exception as e:
        logger.warning(f"[TRANSFORM] Could not save clean CSV: {e}")

    # ── Step 3: Load ──────────────────────────────────────────────────────────
    if args.no_load:
        logger.info("[LOAD] Skipped (--no-load flag set)")
    else:
        try:
            step_load(df, db_url=db_url, logger=logger)
        except Exception as e:
            logger.error(f"[LOAD] FAILED: {e}", exc_info=True)
            logger.warning("Skipping archive step since load failed.")
            sys.exit(1)

    # ── Step 4: Archive ───────────────────────────────────────────────────────
    if args.no_archive or args.no_load:
        logger.info("[ARCHIVE] Skipped.")
    else:
        try:
            step_archive(raw_csv, explored_dir, today, logger=logger)
        except Exception as e:
            logger.warning(f"[ARCHIVE] Could not move raw file: {e}")

    logger.info("=" * 60)
    logger.info("ETL Pipeline completed successfully.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
