"""
AvtoElon.uz Car Scraper
-----------------------
Scrapes car listings from https://avtoelon.uz/avto/ and saves to CSV.

Usage:
    python scraper/avtoelon_scraper.py                # full run
    python scraper/avtoelon_scraper.py --test 10      # scrape 10 listings only
    python scraper/avtoelon_scraper.py --pages 5      # scrape first 5 pages only

Architecture:
    AvtoelonScraper
    ├── __init__()          – session, load existing IDs, setup logging
    ├── _get()              – robust HTTP fetch with retries + backoff
    ├── _get_listing_urls() – scrape one search page → collect detail URLs
    ├── _parse_detail()     – parse one listing page → dict row
    ├── _save()             – atomic append to CSV
    └── run()               – main page→detail loop
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup

# Allow running from repo root: `python scraper/avtoelon_scraper.py`
sys.path.insert(0, os.path.dirname(__file__))
import config as cfg


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────
def _setup_logging(log_file: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger("avtoelon")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
_WHITESPACE_RE = re.compile(r"\s+")
_NUMERIC_RE    = re.compile(r"[\d.,]+")


def _clean_text(text: str) -> str:
    """Strip and collapse whitespace."""
    return _WHITESPACE_RE.sub(" ", text).strip() if text else ""


def _extract_number(text: str) -> Optional[str]:
    """Pull the first numeric value (keep decimal point, drop spaces)."""
    if not text:
        return None
    t = text.replace("\xa0", "").replace(" ", "")
    m = _NUMERIC_RE.search(t)
    return m.group(0).replace(",", ".") if m else None


def _extract_currency(text: str) -> str:
    t = text.lower()
    for key, val in cfg.CURRENCY_MAP.items():
        if key in t:
            return val
    return "USD"   # avtoelon default is y.e. = USD


def _extract_ad_id(url: str) -> Optional[str]:
    m = re.search(r"/a/show/(\d+)", url)
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Scraper class
# ─────────────────────────────────────────────────────────────────────────────
class AvtoelonScraper:

    def __init__(self, output_file: str = cfg.OUTPUT_FILE):
        self.output_file = output_file
        self.logger = _setup_logging(cfg.LOG_FILE)
        self._shutdown = False

        # Persistent HTTP session — reuses connections + cookies
        self.session = requests.Session()
        self.session.headers.update(cfg.HEADERS)

        # Deduplication: load IDs already in the CSV before any HTTP work
        self.seen_ids: Set[str] = self._load_existing_ids()
        self.logger.info(f"Loaded {len(self.seen_ids)} existing ad IDs from {output_file}")

        # Ensure CSV exists with header
        self._ensure_csv()

        # Graceful shutdown on Ctrl+C
        signal.signal(signal.SIGINT,  self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ── Shutdown ──────────────────────────────────────────────────────────────
    def _handle_signal(self, *_):
        self.logger.info("Shutdown signal received — finishing current batch then exiting.")
        self._shutdown = True

    # ── CSV helpers ───────────────────────────────────────────────────────────
    def _load_existing_ids(self) -> Set[str]:
        if not os.path.exists(self.output_file):
            return set()
        ids = set()
        try:
            with open(self.output_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("ad_id"):
                        ids.add(row["ad_id"])
        except Exception as e:
            self.logger.error(f"Could not load existing IDs: {e}")
        return ids

    def _ensure_csv(self):
        """Create CSV with header row if it does not yet exist."""
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=cfg.OUTPUT_COLUMNS).writeheader()

    def _save(self, batch: List[Dict]):
        """
        Atomically append a batch of rows to the CSV.
        Writes to a .tmp file first, then renames — protects data on crash.
        """
        if not batch:
            return

        tmp_path = self.output_file + ".tmp"
        try:
            # Read existing content
            existing_rows = []
            if os.path.exists(self.output_file):
                with open(self.output_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)

            # Merge and write to tmp
            all_rows = existing_rows + batch
            with open(tmp_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cfg.OUTPUT_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_rows)

            # Atomic replace
            os.replace(tmp_path, self.output_file)
            self.logger.info(f"Saved {len(batch)} new rows → {self.output_file} (total {len(all_rows)})")

        except Exception as e:
            self.logger.error(f"Save failed: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── HTTP ──────────────────────────────────────────────────────────────────
    def _get(self, url: str, retries: int = cfg.MAX_RETRIES) -> Optional[BeautifulSoup]:
        """
        Fetch a URL with retry logic:
        - 429 → wait Retry-After header (or cfg.RATE_LIMIT_DELAY) then retry
        - 404/410 → return None (ad deleted)
        - 5xx / connection error → exponential backoff
        """
        delay = 1.0
        for attempt in range(1, retries + 2):
            try:
                resp = self.session.get(url, timeout=15)

                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, "html.parser")

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", cfg.RATE_LIMIT_DELAY))
                    self.logger.warning(f"Rate limited (429) — waiting {wait}s")
                    time.sleep(wait)
                    continue

                if resp.status_code in (403, 404, 410):
                    self.logger.debug(f"HTTP {resp.status_code}: {url}")
                    return None

                self.logger.warning(f"HTTP {resp.status_code} on {url} (attempt {attempt})")

            except requests.ConnectionError as e:
                self.logger.warning(f"Connection error on {url} (attempt {attempt}): {e}")
            except requests.Timeout:
                self.logger.warning(f"Timeout on {url} (attempt {attempt})")
            except Exception as e:
                self.logger.error(f"Unexpected error on {url}: {e}")
                return None

            if attempt <= retries:
                time.sleep(delay)
                delay = min(delay * cfg.BACKOFF_FACTOR, 60)

        self.logger.error(f"Gave up after {retries} retries: {url}")
        return None

    # ── Link collection ───────────────────────────────────────────────────────
    def _get_listing_urls(self, page: int) -> List[str]:
        """
        Fetch one search results page and return unique detail URLs.
        Returns an empty list if the page has no listings (signals end of pagination).
        """
        url  = f"{cfg.SEARCH_URL}?page={page}"
        soup = self._get(url)
        if not soup:
            return []

        hrefs = []
        for a in soup.find_all("a", href=re.compile(r"/a/show/\d+")):
            href = a["href"]
            if not href.startswith("http"):
                href = cfg.BASE_URL + href
            hrefs.append(href)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for h in hrefs:
            if h not in seen:
                seen.add(h)
                unique.append(h)

        self.logger.info(f"Page {page}: found {len(unique)} listing URLs")
        return unique

    # ── Detail page parser ────────────────────────────────────────────────────
    def _parse_detail(self, url: str) -> Optional[Dict]:
        """
        Parse one listing page into a flat dict matching cfg.OUTPUT_COLUMNS.

        Strategy (layered):
          1. `window.digitalData` embedded JSON  → brand, model, date, status, price, image
          2. <dt>/<dd> pairs                      → year, mileage, engine, transmission, etc.
          3. <ol> breadcrumb                      → sale_type
          4. price element (.a-price__text)       → price + currency
          5. og:image meta                        → image_url fallback
        """
        soup = self._get(url)
        if not soup:
            return None

        # Check if ad is deleted / inactive
        text_lower = soup.get_text(" ", strip=True).lower()
        inactive_phrases = (
            "объявление не найдено", "объявление удалено",
            "объявление больше не доступно", "e'lon mavjud emas",
            "sahifa topilmadi",
        )
        if any(p in text_lower for p in inactive_phrases):
            self.logger.debug(f"Inactive ad skipped: {url}")
            return None

        row: Dict = {col: None for col in cfg.OUTPUT_COLUMNS}
        row["url"]    = url
        row["ad_id"]  = _extract_ad_id(url)
        row["source"] = "avtoelon"

        # ── 1. digitalData JSON ───────────────────────────────────────────────
        for script in soup.find_all("script"):
            src = script.string or ""
            m = re.search(r"window\.digitalData\s*=\s*(\{.*?\});", src, re.DOTALL)
            if m:
                try:
                    dd = json.loads(m.group(1))
                    product = dd.get("product", {})
                    attrs   = product.get("attributes", {})

                    row["brand"] = attrs.get("brand")
                    row["model"] = attrs.get("model")

                    # Price from digitalData
                    price_val = product.get("unitPrice")
                    if price_val:
                        row["price"]    = str(price_val)
                        row["currency"] = "USD"   # unitPrice on avtoelon is always USD

                    # Date — lastUpdate is ISO 8601
                    last_update = product.get("lastUpdate", "")
                    if last_update:
                        try:
                            dt = datetime.fromisoformat(last_update)
                            row["posting_date"] = dt.strftime("%d.%m.%Y")
                        except ValueError:
                            row["posting_date"] = last_update[:10]

                    # Image — second og:image is the real car photo
                    photos = product.get("photos", 0)
                    if photos:
                        og_images = [
                            t.get("content", "")
                            for t in soup.find_all("meta", property="og:image")
                        ]
                        # First og:image is the site logo; second is the car photo
                        if len(og_images) >= 2:
                            row["image_url"] = og_images[1]
                        elif og_images:
                            row["image_url"] = og_images[0]

                except (json.JSONDecodeError, KeyError):
                    pass
                break   # only one digitalData block

        # ── 2. <dt>/<dd> parameter pairs ─────────────────────────────────────
        for dt in soup.find_all("dt"):
            label = _clean_text(dt.get_text()).lower()
            dd    = dt.find_next_sibling("dd")
            if not dd:
                continue
            value = _clean_text(dd.get_text())

            field = cfg.FIELD_MAP.get(label)
            if not field:
                continue

            if field == "mileage":
                row["mileage"] = _extract_number(value)
            elif field == "engine_volume":
                # "1.5(Бензин)" → engine_volume=1.5, fuel_type from parens
                row["engine_volume"] = _extract_number(value)
                fuel_m = re.search(r"\(([^)]+)\)", value)
                if fuel_m and not row.get("fuel_type"):
                    row["fuel_type"] = _clean_text(fuel_m.group(1))
            elif field == "year":
                row["year"] = _extract_number(value)
            else:
                row[field] = value

        # ── 3. Breadcrumb → region + sale_type ───────────────────────────────
        breadcrumbs = soup.find_all("ol")
        for ol in breadcrumbs:
            items = [li.get_text(strip=True) for li in ol.find_all("li")]
            if not items:
                continue

            # First breadcrumb: [Главная, Легковые, <sale_type>, <brand>, <model>, ...]
            if len(items) >= 3:
                # sale_type is the 3rd breadcrumb item if it's not a brand name
                candidate = items[2].lower()
                for key, val in cfg.SALE_TYPE_MAP.items():
                    if key in candidate:
                        row["sale_type"] = val
                        break
                else:
                    row["sale_type"] = "sale"   # default: regular sale

            # Second breadcrumb contains location e.g. "Легковые в Ташкенте"
            if len(items) >= 2:
                loc_text = items[1]  # e.g. "Легковые в Ташкенте"
                loc_m = re.search(r"\bв\s+(.+)$", loc_text)
                if loc_m:
                    row["district"] = loc_m.group(1)

            break   # only need the first ol

        # ── 4. Price element (if digitalData had no price) ────────────────────
        if not row.get("price"):
            price_el = soup.find(class_="a-price__text")
            if not price_el:
                price_el = soup.find(class_="a-price")
            if price_el:
                price_text = price_el.get_text(strip=True)
                row["price"]    = _extract_number(price_text)
                row["currency"] = _extract_currency(price_text)

        # ── 5. image_url fallback ─────────────────────────────────────────────
        if not row.get("image_url"):
            og = soup.find("meta", property="og:image")
            if og:
                row["image_url"] = og.get("content")

        # ── 6. Description from meta tag ──────────────────────────────────────
        if not row.get("description"):
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                row["description"] = meta_desc.get("content", "")

        return row

    # ── Main run loop ─────────────────────────────────────────────────────────
    def run(self, max_pages: int = cfg.MAX_PAGES, test_limit: Optional[int] = None):
        """
        Main execution loop.
        - Paginates through search results pages.
        - Skips detail URLs whose ad_id is already in seen_ids.
        - Saves in batches of cfg.BATCH_SIZE.
        - Stops early if test_limit is reached.
        """
        self.logger.info("=" * 60)
        self.logger.info("AvtoElon scraper started")
        if test_limit:
            self.logger.info(f"TEST MODE — will stop after {test_limit} new listings")
        self.logger.info("=" * 60)

        total_new   = 0
        batch: List[Dict] = []

        for page in range(1, max_pages + 1):
            if self._shutdown:
                break

            listing_urls = self._get_listing_urls(page)

            # Empty page → we've gone past the last page
            if not listing_urls:
                self.logger.info(f"No listings on page {page} — stopping pagination.")
                break

            for url in listing_urls:
                if self._shutdown:
                    break

                ad_id = _extract_ad_id(url)

                # Skip already-scraped listings BEFORE making the expensive detail request
                if ad_id and ad_id in self.seen_ids:
                    self.logger.debug(f"Skip (seen): {url}")
                    continue

                row = self._parse_detail(url)
                if row:
                    batch.append(row)
                    if ad_id:
                        self.seen_ids.add(ad_id)
                    total_new += 1
                    self.logger.info(f"[{total_new}] Scraped: {url}")

                    if test_limit and total_new >= test_limit:
                        self.logger.info(f"Test limit ({test_limit}) reached.")
                        self._save(batch)
                        return

                # Polite delay between detail requests
                time.sleep(random.uniform(*cfg.DEFAULT_DELAY))

            # Save after every page batch
            if batch:
                self._save(batch)
                batch = []

            self.logger.info(f"Finished page {page}/{max_pages} — {total_new} new total")

            # Polite delay between search pages
            time.sleep(random.uniform(*cfg.DEFAULT_DELAY))

        # Final flush
        if batch:
            self._save(batch)

        self.logger.info(f"Done. Total new listings scraped: {total_new}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AvtoElon.uz car scraper")
    parser.add_argument(
        "--test", type=int, metavar="N", default=None,
        help="Stop after scraping N new listings (for quick verification)"
    )
    parser.add_argument(
        "--pages", type=int, default=cfg.MAX_PAGES,
        help=f"Maximum pages to scrape (default: {cfg.MAX_PAGES})"
    )
    parser.add_argument(
        "--output", type=str, default=cfg.OUTPUT_FILE,
        help=f"Output CSV file path (default: {cfg.OUTPUT_FILE})"
    )
    args = parser.parse_args()

    scraper = AvtoelonScraper(output_file=args.output)
    scraper.run(max_pages=args.pages, test_limit=args.test)


if __name__ == "__main__":
    main()
