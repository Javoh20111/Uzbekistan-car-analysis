"""
Car Scraper Module — OLX.uz

NOTE: This file lives in scraper/. Run from the project root:
    python scraper/olx_scraper.py --test 5
    python scraper/olx_scraper.py

PRIMARY strategy  : parse the __NEXT_DATA__ JSON that Next.js embeds in every
                    page.  This is far more stable than CSS class names, which
                    OLX rotates on every deploy.
FALLBACK strategy : data-testid / data-cy attributes (also stable).

Usage:
    python car_scraper.py                  # full run (all links)
    python car_scraper.py --test 5         # scrape only 5 cars — quick check
    python car_scraper.py --test 10 --output test_output.json
"""

import argparse
import atexit
import json
import logging
import os
import platform
import random
import re
import signal
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global driver handle
# ---------------------------------------------------------------------------
driver = None

ACTIVE_LINKS_FILE = os.path.join(os.path.dirname(__file__), "data", "olx_active_links.json")
INACTIVE_LINKS_FILE = os.path.join(os.path.dirname(__file__), "data", "olx_inactive_links.json")
LINK_STATUS_SAVE_INTERVAL = 100


class InactiveAdError(Exception):
    """Raised when OLX says an ad URL is deleted or no longer available."""


# ---------------------------------------------------------------------------
# Signal / cleanup
# ---------------------------------------------------------------------------
def cleanup():
    global driver
    if driver:
        logger.info("Closing Chrome driver…")
        try:
            driver.quit()
            driver = None
        except Exception as e:
            logger.error(f"Error closing driver: {e}")
            if platform.system() != "Windows":
                subprocess.run(["pkill", "-f", "chrome"], check=False)


def signal_handler(signum, frame):
    logger.info("Interrupt received. Cleaning up…")
    cleanup()
    exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
def load_translations() -> Dict:
    try:
        path = os.path.join(os.path.dirname(__file__), "translations.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading translations: {e}")
        return {}


TRANSLATIONS = load_translations()


def translate(value: str, category: str) -> str:
    if not value or category not in TRANSLATIONS:
        return value
    if category == "additional_options":
        parts = [opt.strip() for opt in value.split(",")]
        return ", ".join(TRANSLATIONS[category].get(p, p) for p in parts)
    return TRANSLATIONS[category].get(value, value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}
CYRILLIC_TO_LATIN.update({k.upper(): v.capitalize() for k, v in CYRILLIC_TO_LATIN.items()})


def to_latin(text: str) -> Optional[str]:
    if not text:
        return None
    return "".join(CYRILLIC_TO_LATIN.get(c, c) for c in text)


def extract_numeric(text: str) -> Optional[str]:
    if not text:
        return None
    n = re.sub(r"[^\d.]", "", text)
    return n if n else None


def extract_currency(text: str) -> Optional[str]:
    if not text:
        return None
    if "$" in text:
        return "USD"
    if "€" in text:
        return "EUR"
    if "₽" in text:
        return "RUB"
    if "сум" in text.lower() or "uzs" in text.lower():
        return "UZS"
    if "у.е." in text.lower():
        return "USD"
    return None


MONTH_MAP = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}


def format_date(text: str) -> Optional[str]:
    try:
        text = text.replace(" г.", "").strip()
        parts = text.split()
        if len(parts) == 3:
            day, month_ru, year = parts
            month = MONTH_MAP.get(month_ru.lower(), "01")
            return f"{int(day):02d}.{month}.{year}"
    except Exception:
        pass
    return text


def clean_location(text: str) -> Optional[str]:
    if not text:
        return None
    return text.replace(",", "").replace(".", "").strip()


def _read_json_list(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, str)]
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
    return []


def _write_json_list(path: str, links: List[str]):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")


def save_link_status(active_urls: set, inactive_urls: set):
    _write_json_list(ACTIVE_LINKS_FILE, sorted(active_urls))
    _write_json_list(INACTIVE_LINKS_FILE, sorted(inactive_urls))


def save_deleted_ad(url: str):
    path = os.path.join(os.path.dirname(__file__), "deleted_ads.json")
    try:
        data = {"deleted_ads": []}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        if url not in data["deleted_ads"]:
            data["deleted_ads"].append(url)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving deleted ad: {e}")


def is_inactive_page(soup: BeautifulSoup) -> bool:
    inactive_msg = soup.find(attrs={"data-testid": "ad-inactive-msg"})
    if inactive_msg:
        return True

    body_text = soup.get_text(" ", strip=True).lower()
    inactive_phrases = (
        "страница не найдена",
        "объявление не найдено",
        "объявление больше не доступно",
        "объявление удалено",
        "удалено",
        "e'lon mavjud emas",
        "elon mavjud emas",
        "sahifa topilmadi",
    )
    return any(phrase in body_text for phrase in inactive_phrases)


# ---------------------------------------------------------------------------
# __NEXT_DATA__ parser  ← THE REAL FIX
# ---------------------------------------------------------------------------
# OLX.uz is a Next.js app. Every page embeds a <script id="__NEXT_DATA__">
# block containing the full structured listing data as JSON.
# Parsing this is immune to CSS class renames.

# Maps OLX param keys → our field names
_PARAM_KEY_MAP = {
    # car characteristics
    "model":           "model",
    "car_model":       "model",
    "enginesize":      "engine_volume",
    "engine_size":     "engine_volume",
    "petrol":          "fuel_type",
    "fuel_type":       "fuel_type",
    "transmission":    "transmission",
    "gearbox":         "transmission",
    "color":           "color",
    "body_type":       "body_type",
    "car_type":        "body_type",
    "mileage":         "mileage",
    "milage":          "mileage",
    "year":            "year",
    "manufacture_year":"year",
    "condition":       "condition",
    "car_condition":   "condition",
    "number_of_owners": "owners_count",
    "owners":          "owners_count",
    "sale_type":       "sale_type",
    "offer_type":      "sale_type",
    # seller
    "advertiser_type": "seller_type",
    "user_type":       "seller_type",
}

# Maps raw label values → our translation categories
_LABEL_CATEGORY = {
    "body_type":    "body_type",
    "fuel_type":    "fuel_type",
    "transmission": "transmission",
    "color":        "color",
    "condition":    "condition",
    "sale_type":    "sale_type",
    "seller_type":  "seller_type",
}

_SELLER_MAP = {
    "private":   "private",
    "business":  "business",
    "individual": "private",
    "person":    "private",
    "user":      "private",
    "company":   "business",
    "dealer":    "business",
    "частное лицо": "private",
    "бизнес":    "business",
    "jismoniy shaxs": "private",
    "biznes":    "business",
}

_IMAGE_URL_RE = re.compile(r"https?:\/\/[^\s\"'<>]+olxcdn\.com[^\s\"'<>]*", re.IGNORECASE)


def _normalize_seller_type(value: str) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value).strip().lower()
    if normalized in _SELLER_MAP:
        return _SELLER_MAP[normalized]
    if "частное лицо" in normalized or "jismoniy shaxs" in normalized:
        return "private"
    if "бизнес" in normalized or "biznes" in normalized:
        return "business"
    return None


def _normalize_image_url(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None

    value = value.strip()
    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("http://", "https://")):
        match = _IMAGE_URL_RE.search(value)
        value = match.group(0) if match else value

    if "olxcdn.com" not in value or value.startswith("data:"):
        return None

    return (
        value.replace("{width}", "800")
        .replace("{height}", "600")
        .replace("&amp;", "&")
    )


def _find_first_image_url(obj: Any) -> Optional[str]:
    if isinstance(obj, str):
        return _normalize_image_url(obj)
    if isinstance(obj, list):
        for item in obj:
            url = _find_first_image_url(item)
            if url:
                return url
    if isinstance(obj, dict):
        preferred_keys = (
            "link", "url", "src", "href", "imageUrl", "image_url",
            "original", "large", "medium", "small", "thumbnail",
        )
        for key in preferred_keys:
            if key in obj:
                url = _find_first_image_url(obj[key])
                if url:
                    return url
        for value in obj.values():
            url = _find_first_image_url(value)
            if url:
                return url
    return None


def _parse_next_data(data: dict) -> dict:
    """Extract car fields from OLX __NEXT_DATA__ JSON."""
    result = {}
    try:
        ad = data["props"]["pageProps"]["ad"]
    except (KeyError, TypeError):
        return result

    # --- price ---
    price_block = ad.get("price") or {}
    raw_price = price_block.get("value")
    result["price"]    = extract_numeric(str(raw_price)) if raw_price else None
    result["currency"] = price_block.get("currency") or None

    # --- description ---
    desc = (ad.get("description") or "").strip()
    result["description"] = desc[:2000] if desc else None

    # --- params list ---
    for param in ad.get("params") or []:
        key   = (param.get("key") or "").lower()
        field = _PARAM_KEY_MAP.get(key)
        if not field:
            continue
        value_obj = param.get("value") or {}
        label = (value_obj.get("label") or "").strip()
        if not label:
            label = str(value_obj.get("key") or "").strip()
        if not label:
            continue
        cat = _LABEL_CATEGORY.get(field)
        if field == "seller_type":
            result[field] = _normalize_seller_type(label) or translate(label, cat) or label
        else:
            result[field] = translate(label, cat) if cat else label

    # --- seller type from ad.advertiser (alternative location) ---
    if "seller_type" not in result:
        adv = ad.get("advertiser") or {}
        for key in ("accountType", "account_type", "type", "userType", "user_type"):
            seller_type = _normalize_seller_type(str(adv.get(key) or ""))
            if seller_type:
                result["seller_type"] = seller_type
                break

    # --- location ---
    loc = ad.get("location") or {}
    region_raw   = (loc.get("region")   or {}).get("name") or ""
    district_raw = (loc.get("district") or {}).get("name") or \
                   (loc.get("city")     or {}).get("name") or ""
    result["region"]   = translate(region_raw.strip(),   "regions")   if region_raw   else None
    result["district"] = translate(district_raw.strip(), "districts") if district_raw else None

    # --- posting date ---
    date_raw = ad.get("createdTime") or ad.get("lastRefreshTime") or ""
    if date_raw:
        try:
            dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            result["posting_date"] = dt.strftime("%d.%m.%Y")
        except Exception:
            result["posting_date"] = date_raw[:10]

    # --- image ---
    for key in ("photos", "images", "image", "media", "gallery"):
        image_url = _find_first_image_url(ad.get(key))
        if image_url:
            result["image_url"] = image_url
            break

    return result


# ---------------------------------------------------------------------------
# HTML fallback parsers  (used when __NEXT_DATA__ is missing/incomplete)
# ---------------------------------------------------------------------------

def _fallback_price(soup: BeautifulSoup) -> tuple:
    """Try data-testid first, then any element containing a price pattern."""
    # data-testid="ad-price-container" is stable
    el = soup.find(attrs={"data-testid": "ad-price-container"})
    if not el:
        el = soup.find(attrs={"data-cy": "ad-price"})
    if el:
        text = el.get_text(strip=True)
        return extract_numeric(text), extract_currency(text)

    # Generic: find a short element that looks like a price
    pattern = re.compile(r"[\d\s,.]{4,}.*(?:USD|\$|сум|у\.е\.)", re.IGNORECASE)
    for tag in soup.find_all(["h3", "strong", "span", "div"]):
        text = tag.get_text(strip=True)
        if pattern.search(text) and len(text) < 50:
            return extract_numeric(text), extract_currency(text)
    return None, None


def _fallback_description(soup: BeautifulSoup) -> Optional[str]:
    for attr, val in [("data-cy", "ad_description"), ("data-testid", "ad-description")]:
        el = soup.find(attrs={attr: val})
        if el:
            t = el.get_text(separator=" ", strip=True)
            if len(t) > 20:
                return t[:2000]
    for el in soup.find_all(["div", "section"]):
        cls = " ".join(el.get("class", []))
        if "description" in cls.lower():
            t = el.get_text(separator=" ", strip=True)
            if len(t) > 20:
                return t[:2000]
    return None


def _fallback_location(soup: BeautifulSoup) -> tuple:
    region, district = None, None
    el = soup.find(attrs={"data-testid": "map-aside-section"})
    if el:
        texts = [p.get_text(strip=True) for p in el.find_all("p") if p.get_text(strip=True) != "Местоположение"]
        if len(texts) >= 2:
            district = clean_location(texts[0])
            region   = translate(clean_location(texts[1]), "regions")
        elif len(texts) == 1:
            region = translate(clean_location(texts[0]), "regions")
    return region, district


def _fallback_posting_date(soup: BeautifulSoup) -> Optional[str]:
    el = soup.find(attrs={"data-testid": "ad-posted-at"})
    if el:
        return format_date(el.get_text(strip=True))
    return None


def _fallback_image_url(soup: BeautifulSoup) -> Optional[str]:
    for attrs in (
        {"property": "og:image"},
        {"property": "og:image:url"},
        {"name": "twitter:image"},
        {"name": "twitter:image:src"},
    ):
        el = soup.find("meta", attrs=attrs)
        if el:
            image_url = _normalize_image_url(el.get("content"))
            if image_url:
                return image_url

    for el in soup.find_all(["img", "source", "link"]):
        for attr in ("src", "srcset", "data-src", "href", "imagesrcset"):
            value = el.get(attr)
            if not value:
                continue
            for candidate in str(value).split(","):
                image_url = _normalize_image_url(candidate.strip().split(" ")[0])
                if image_url:
                    return image_url

    match = _IMAGE_URL_RE.search(str(soup))
    return _normalize_image_url(match.group(0)) if match else None


def _fallback_seller_type(soup: BeautifulSoup) -> Optional[str]:
    for selector in (
        '[data-testid*="seller"]',
        '[data-testid*="user"]',
        '[data-cy*="seller"]',
        '[data-cy*="user"]',
    ):
        for el in soup.select(selector):
            seller_type = _normalize_seller_type(el.get_text(" ", strip=True))
            if seller_type:
                return seller_type

    return _normalize_seller_type(soup.get_text(" ", strip=True))


def _fallback_params(soup: BeautifulSoup) -> dict:
    """Parse the ad-parameters-container using stable data-testid."""
    result = {}
    container = soup.find(attrs={"data-testid": "ad-parameters-container"})
    if not container:
        return result

    # OLX renders params as <li> or <p> items with label:value text
    for el in container.find_all(["p", "li", "span"]):
        text = el.get_text(separator=":", strip=True)
        if ":" not in text:
            continue
        label_raw, _, value_raw = text.partition(":")
        label = label_raw.strip()
        value = value_raw.strip()
        if not value:
            continue

        low = label.lower()
        if "модел" in low:
            result["model"] = value
        elif "тип кузова" in low:
            result["body_type"] = translate(value, "body_type")
        elif "год выпуска" in low or "год" in low:
            result["year"] = value
        elif "пробег" in low:
            result["mileage"] = extract_numeric(value)
        elif "коробка" in low:
            result["transmission"] = translate(value, "transmission")
        elif "цвет" in low:
            result["color"] = translate(value, "color")
        elif "объем двигателя" in low or "двигател" in low:
            result["engine_volume"] = extract_numeric(value)
        elif "вид топлива" in low or "топлив" in low:
            result["fuel_type"] = translate(value, "fuel_type")
        elif "состояние" in low:
            result["condition"] = translate(value, "condition")
        elif "хозяев" in low or "владелец" in low:
            result["owners_count"] = value
        elif "условия продажи" in low:
            result["sale_type"] = translate(value, "sale_type")
        elif "доп" in low and "опци" in low:
            result["additional_options"] = translate(value, "additional_options")
        else:
            seller_type = _normalize_seller_type(text)
            if seller_type:
                result["seller_type"] = seller_type

    return result


# ---------------------------------------------------------------------------
# Chrome driver
# ---------------------------------------------------------------------------
def initialize_driver() -> webdriver.Chrome:
    global driver
    cleanup()

    opts = Options()
    if platform.system() != "Darwin":
        opts.add_argument("--headless=new")
    for arg in [
        "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
        "--window-size=1920,1080", "--disable-extensions",
        "--ignore-certificate-errors",
    ]:
        opts.add_argument(arg)

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    opts.add_argument(f"--user-agent={ua}")

    for attempt in range(1, 4):
        try:
            driver = webdriver.Chrome(options=opts)
            driver.set_page_load_timeout(25)
            driver.set_script_timeout(25)
            driver.get("https://www.google.com")
            logger.info("Chrome driver ready")
            return driver
        except Exception as e:
            logger.error(f"Driver init attempt {attempt}/3: {e}")
            if attempt == 3:
                raise
            time.sleep(5)


# ---------------------------------------------------------------------------
# Core scrape function
# ---------------------------------------------------------------------------
def get_car_info(url: str, drv: webdriver.Chrome, max_retries: int = 3) -> Optional[Dict]:
    for attempt in range(1, max_retries + 2):
        try:
            drv.delete_all_cookies()
            drv.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
            drv.get(url)
            WebDriverWait(drv, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            logger.warning(f"Timeout loading {url} (attempt {attempt})")
            if attempt > max_retries:
                return None
            time.sleep(3)
            continue
        except WebDriverException as e:
            err = str(e).lower()
            if "no such window" in err or "invalid session" in err:
                logger.warning("Session lost — reinitialising driver")
                drv = initialize_driver()
            if attempt > max_retries:
                return None
            time.sleep(3)
            continue

        try:
            soup = BeautifulSoup(drv.page_source, "lxml")
        except Exception:
            soup = BeautifulSoup(drv.page_source, "html.parser")


        # --- deleted / inactive check ---
        if is_inactive_page(soup):
            logger.warning(f"Inactive/deleted ad: {url}")
            save_deleted_ad(url)
            raise InactiveAdError(url)

        # ----------------------------------------------------------------
        # STEP 1: parse __NEXT_DATA__ JSON  ← primary, most reliable
        # ----------------------------------------------------------------
        car = {}
        next_script = soup.find("script", id="__NEXT_DATA__")
        if next_script:
            try:
                ndata = json.loads(next_script.string or "")
                car = _parse_next_data(ndata)
                logger.info(f"  __NEXT_DATA__ parsed — fields found: {[k for k,v in car.items() if v]}")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"  __NEXT_DATA__ parse error: {e}")
        else:
            logger.warning("  __NEXT_DATA__ script NOT found — using HTML fallbacks only")

        # ----------------------------------------------------------------
        # STEP 2: fill any gaps with HTML fallbacks
        # ----------------------------------------------------------------
        if not car.get("price"):
            p, c = _fallback_price(soup)
            car["price"], car["currency"] = p, c

        if not car.get("description"):
            car["description"] = _fallback_description(soup)

        if not car.get("region"):
            r, d = _fallback_location(soup)
            car.setdefault("region", r)
            car.setdefault("district", d)

        if not car.get("posting_date"):
            car["posting_date"] = _fallback_posting_date(soup)

        if not car.get("image_url"):
            car["image_url"] = _fallback_image_url(soup)

        if not car.get("seller_type"):
            car["seller_type"] = _fallback_seller_type(soup)

        # Fill remaining car-specific fields from HTML params
        html_params = _fallback_params(soup)
        for field, val in html_params.items():
            if not car.get(field):
                car[field] = val

        # ----------------------------------------------------------------
        # Build final record with all expected columns
        # ----------------------------------------------------------------
        record = {
            "url":               url,
            "posting_date":      car.get("posting_date"),
            "region":            car.get("region"),
            "district":          car.get("district"),
            "price":             car.get("price"),
            "currency":          car.get("currency"),
            "description":       car.get("description"),
            "image_url":         car.get("image_url"),
            "seller_type":       car.get("seller_type"),
            "model":             car.get("model"),
            "body_type":         car.get("body_type"),
            "sale_type":         car.get("sale_type"),
            "year":              car.get("year"),
            "mileage":           car.get("mileage"),
            "transmission":      car.get("transmission"),
            "color":             car.get("color"),
            "engine_volume":     car.get("engine_volume"),
            "fuel_type":         car.get("fuel_type"),
            "condition":         car.get("condition"),
            "owners_count":      car.get("owners_count"),
            "additional_options":car.get("additional_options"),
        }

        filled = sum(1 for v in record.values() if v is not None)
        logger.info(f"  → {filled}/{len(record)} fields filled for {url.split('/')[-1]}")
        return record

    return None


# ---------------------------------------------------------------------------
# Bulk processing
# ---------------------------------------------------------------------------
def load_car_links(json_file: str) -> List[str]:
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "links" in data:
            return data["links"]
        if isinstance(data, list):
            return data
    except Exception as e:
        logger.error(f"Error loading links: {e}")
    return []


def load_existing_data(output_file: str) -> List[Dict]:
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    return []


def process_car_links(links: List[str], output_file: str = "car_data.json", test_limit: int = None):
    """
    Process car links and save results.

    Args:
        links:       list of OLX car URLs
        output_file: path to output JSON
        test_limit:  if set, stop after this many new records (for quick testing)
    """
    global driver

    existing_data  = load_existing_data(output_file)
    processed_urls = {item["url"] for item in existing_data}
    active_urls = set(_read_json_list(ACTIVE_LINKS_FILE))
    inactive_urls = set(_read_json_list(INACTIVE_LINKS_FILE))
    active_urls.update(processed_urls)

    driver = initialize_driver()
    consecutive_fails = 0
    processed_since_restart = 0
    new_count = 0

    if test_limit:
        logger.info(f"🧪 TEST MODE — will stop after {test_limit} new records")

    for i, link in enumerate(links, 1):
        if link in processed_urls:
            logger.info(f"Skip (already scraped) {i}/{len(links)}: {link}")
            continue

        if link in inactive_urls:
            logger.info(f"Skip (known inactive) {i}/{len(links)}: {link}")
            continue

        if test_limit and new_count >= test_limit:
            logger.info(f"✅ Test limit of {test_limit} reached. Stopping.")
            break

        # Periodic driver restart
        if consecutive_fails >= 10:
            logger.warning("Too many failures — restarting driver")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(3)
            driver = initialize_driver()
            consecutive_fails = 0
            processed_since_restart = 0
            time.sleep(15)
        elif processed_since_restart >= 100:
            logger.info("Routine browser refresh after 100 items")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(3)
            driver = initialize_driver()
            processed_since_restart = 0
            time.sleep(3)

        logger.info(f"Processing {i}/{len(links)}: {link}")

        try:
            # Keep driver alive check
            try:
                _ = driver.current_url
            except Exception:
                driver = initialize_driver()

            try:
                car_info = get_car_info(link, driver)
            except InactiveAdError:
                inactive_urls.add(link)
                active_urls.discard(link)
                save_link_status(active_urls, inactive_urls)
                consecutive_fails = 0
                processed_since_restart += 1
                logger.info(f"  Marked inactive → {INACTIVE_LINKS_FILE}")
                continue

            if car_info:
                existing_data.append(car_info)
                active_urls.add(link)
                inactive_urls.discard(link)
                new_count += 1
                consecutive_fails = 0
                processed_since_restart += 1

                # Save after every record
                tmp = output_file + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, output_file)
                if new_count % LINK_STATUS_SAVE_INTERVAL == 0:
                    save_link_status(active_urls, inactive_urls)
                logger.info(f"  Saved record #{new_count} → {output_file}")
            else:
                consecutive_fails += 1
                logger.warning(f"  No data — fails streak: {consecutive_fails}")

        except Exception as e:
            logger.error(f"Error on {link}: {e}")
            consecutive_fails += 1

        time.sleep(random.uniform(1.0, 2.5))

    save_link_status(active_urls, inactive_urls)
    logger.info(f"Done — {new_count} new records saved to {output_file}")
    cleanup()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OLX.uz car scraper")
    parser.add_argument(
        "--test", type=int, default=None, metavar="N",
        help="Quick-test mode: stop after N new records (e.g. --test 5)",
    )
    parser.add_argument(
        "--links", default="car_links.json",
        help="Path to JSON file containing car links (default: car_links.json)",
    )
    parser.add_argument(
        "--output", default="data/Prepared/car_data.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    links_path  = os.path.join(base_dir, args.links)
    output_path = os.path.join(base_dir, args.output)

    car_links = load_car_links(links_path)
    logger.info(f"Loaded {len(car_links)} links from {links_path}")

    if args.test:
        # For test mode, use a separate output file so we don't pollute main data
        if args.output == "data/Prepared/car_data.json":
            output_path = os.path.join(base_dir, "data/Prepared/car_data_test.json")
        logger.info(f"Test output → {output_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    process_car_links(car_links, output_file=output_path, test_limit=args.test)
