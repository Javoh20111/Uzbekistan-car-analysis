"""
Configuration for AvtoElon.uz scraper.
All site-specific knobs are centralised here so the scraper stays clean.
"""
# python3 scraper/avtoelon_scraper.py                                 # full run (~1000 pages)
# python3 scraper/avtoelon_scraper.py --test 50                       # quick test
# python3 scraper/avtoelon_scraper.py --pages 10                      # first 10 pages only


# ── URLs ─────────────────────────────────────────────────────────────────────
BASE_URL   = "https://avtoelon.uz"
SEARCH_URL = "https://avtoelon.uz/avto/"

# ── Scraping limits & timing ──────────────────────────────────────────────────
MAX_PAGES        = 1000         # avtoelon.uz currently has ~1000 pages
BATCH_SIZE       = 20           # Save to CSV every N listings scraped
DEFAULT_DELAY    = (1.5, 3.0)   # (min, max) seconds — random range between requests
RATE_LIMIT_DELAY = 60           # Seconds to pause when a 429 is received
MAX_RETRIES      = 5            # Per-request retry limit
BACKOFF_FACTOR   = 2.0          # Exponential backoff multiplier

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_FILE = "scraper/data/avtoelon_car_data.csv"
LOG_FILE    = "scraper/data/avtoelon_scraper.log"

# ── HTTP Headers ─────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control":   "max-age=0",
    "Sec-Fetch-Dest":  "document",
    "Sec-Fetch-Mode":  "navigate",
    "Sec-Fetch-Site":  "same-origin",
    "Sec-Fetch-User":  "?1",
    "Upgrade-Insecure-Requests": "1",
}

# ── CSV columns (matches OLX schema exactly for easy merging) ─────────────────
OUTPUT_COLUMNS = [
    "ad_id",
    "url",
    "posting_date",
    "region",
    "district",
    "price",
    "currency",
    "description",
    "image_url",
    "seller_type",
    "brand",
    "model",
    "body_type",
    "sale_type",
    "year",
    "mileage",
    "transmission",
    "color",
    "engine_volume",
    "fuel_type",
    "condition",
    "drive_type",
    "source",
]

# ── Field map: Russian <dt> label → schema key ─────────────────────────────────
# Covers all dt/dd pairs found on detail pages.
FIELD_MAP = {
    "город":                "district",
    "год":                  "year",
    "объем двигателя, л":   "engine_volume",
    "кузов":                "body_type",
    "пробег":               "mileage",
    "коробка передач":      "transmission",
    "состояние краски":     "condition",
    "привод":               "drive_type",
    "вид топлива":          "fuel_type",
    "цвет":                 "color",
    "состояние":            "condition",
}

# ── Sale type map: breadcrumb keyword → sale_type value ──────────────────────
SALE_TYPE_MAP = {
    "аренда с выкупом": "rent_to_own",
    "в кредит":         "credit",
    "обмен":            "exchange",
}

# ── Currency normalisation ────────────────────────────────────────────────────
# Price on avtoelon is displayed as "y.e." which means USD ($)
CURRENCY_MAP = {
    "y.e.": "USD",
    "у.е.": "USD",
    "usd":  "USD",
    "сум":  "UZS",
    "uzs":  "UZS",
    "$":    "USD",
}
