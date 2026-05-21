"""
Car Scraper Module — OLX.uz (Unified Version)
---------------------------------------------
Scrapes car listings from OLX.uz and saves them directly to a unified CSV file.

Consolidates link extraction, price range filtering, cleaning, and detail page 
parsing into a single, unified Class-based scraper structure that mimics the 
clean design of the AvtoElon scraper, completely eliminating intermediate JSONs.

Usage:
    python scraper/olx_scraper.py                # Full run
    python scraper/olx_scraper.py --test 10      # Scrape 10 listings only
"""

import argparse
import csv
import json
import logging
import os
import platform
import random
import re
import signal
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Allow running from repo root
sys.path.insert(0, os.path.dirname(__file__))
import config as cfg

# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────
def _setup_logging(log_file: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger("olx")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s")

    # Clear existing handlers to prevent duplicate logging
    if logger.handlers:
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Helper Maps and Utilities
# ─────────────────────────────────────────────────────────────────────────────
CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}
CYRILLIC_TO_LATIN.update({k.upper(): v.capitalize() for k, v in CYRILLIC_TO_LATIN.items()})

MONTH_MAP = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}

# Maps OLX json keys → our schema field names
PARAM_KEY_MAP = {
    "model": "model",
    "car_model": "model",
    "enginesize": "engine_volume",
    "engine_size": "engine_volume",
    "petrol": "fuel_type",
    "fuel_type": "fuel_type",
    "transmission": "transmission",
    "gearbox": "transmission",
    "color": "color",
    "body_type": "body_type",
    "car_type": "body_type",
    "mileage": "mileage",
    "milage": "mileage",
    "year": "year",
    "manufacture_year": "year",
    "condition": "condition",
    "car_condition": "condition",
    "number_of_owners": "owners_count",
    "owners": "owners_count",
    "sale_type": "sale_type",
    "offer_type": "sale_type",
    "advertiser_type": "seller_type",
    "user_type": "seller_type",
}

LABEL_CATEGORY = {
    "body_type": "body_type",
    "fuel_type": "fuel_type",
    "transmission": "transmission",
    "color": "color",
    "condition": "condition",
    "sale_type": "sale_type",
    "seller_type": "seller_type",
}

SELLER_MAP = {
    "private": "private",
    "business": "business",
    "individual": "private",
    "person": "private",
    "user": "private",
    "company": "business",
    "dealer": "business",
    "частное лицо": "private",
    "бизнес": "business",
    "jismoniy shaxs": "private",
    "biznes": "business",
}

IMAGE_URL_RE = re.compile(r"https?:\/\/[^\s\"'<>]+olxcdn\.com[^\s\"'<>]*", re.IGNORECASE)

DEFAULT_PRICE_RANGES = [
    (1000, 2000), (2000, 3000), (3000, 3500), (3500, 4000), (4000, 4500),
    (4500, 5000), (5000, 5500), (5500, 6000), (6000, 6500), (6500, 7000),
    (7000, 7500), (7500, 8000), (8000, 8500), (8500, 9000), (9000, 9500),
    (9500, 10000), (10000, 11000), (11000, 12000), (12000, 13000), (13000, 14000),
    (14000, 15000), (15000, 16000), (16000, 18000), (18000, 20000), (20000, 22000),
    (22000, 25000), (25000, 30000), (30000, 35000), (35000, 40000), (40000, 50000),
    (50000, 60000), (60000, 80000), (80000, 100000), (100000, 150000), (150000, 9999999)
]


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
    t = text.lower()
    if "$" in t or "у.е." in t or "usd" in t:
        return "USD"
    if "€" in t or "eur" in t:
        return "EUR"
    if "₽" in t or "rub" in t:
        return "RUB"
    if "сум" in t or "uzs" in t:
        return "UZS"
    return None


def clean_location(text: str) -> Optional[str]:
    if not text:
        return None
    return text.replace(",", "").replace(".", "").strip()


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


def load_translations() -> Dict:
    path = os.path.join(os.path.dirname(__file__), "translations.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


TRANSLATIONS = load_translations()


def translate(value: str, category: str) -> str:
    if not value or category not in TRANSLATIONS:
        return value
    if category == "additional_options":
        parts = [opt.strip() for opt in value.split(",")]
        return ", ".join(TRANSLATIONS[category].get(p, p) for p in parts)
    return TRANSLATIONS[category].get(value, value)


class InactiveAdError(Exception):
    """Raised when an ad URL is deleted, inactive, or no longer available."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Scraper Class
# ─────────────────────────────────────────────────────────────────────────────
class OlxScraper:

    def __init__(self, output_file: str = "scraper/data/olx_car_data.csv"):
        self.output_file = output_file
        self.log_file = "scraper/data/olx_scraper.log"
        self.logger = _setup_logging(self.log_file)
        self._shutdown = False

        # Build comprehensive column list dynamically based on config columns
        self.columns = list(cfg.OUTPUT_COLUMNS)
        for col in ["owners_count", "additional_options"]:
            if col not in self.columns:
                self.columns.append(col)

        # deduplicate: load seen ad links from existing output file
        self.seen_ids: Set[str] = self._load_existing_ids()
        self.logger.info(f"Loaded {len(self.seen_ids)} existing ad URLs from {output_file}")

        # Track known inactive links locally to save requests
        self.inactive_urls: Set[str] = set()

        # Ensure CSV exists with header
        self._ensure_csv()

        # Webdriver placeholder
        self.driver = None

        # Setup Graceful shutdown on Ctrl+C / terminations
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ── Shutdown ──────────────────────────────────────────────────────────────
    def _handle_signal(self, *_):
        self.logger.info("Shutdown signal received — finishing current batch then exiting.")
        self._shutdown = True

    # ── CSV helper methods ────────────────────────────────────────────────────
    def _load_existing_ids(self) -> Set[str]:
        if not os.path.exists(self.output_file):
            return set()
        ids = set()
        try:
            with open(self.output_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("url"):
                        ids.add(row["url"])
        except Exception as e:
            self.logger.error(f"Could not load existing IDs from CSV: {e}")
        return ids

    def _ensure_csv(self):
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.columns).writeheader()

    def _save(self, batch: List[Dict]):
        """Atomically merge and append batch to CSV."""
        if not batch:
            return

        tmp_path = self.output_file + ".tmp"
        try:
            existing_rows = []
            if os.path.exists(self.output_file):
                with open(self.output_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)

            all_rows = existing_rows + batch
            with open(tmp_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_rows)

            os.replace(tmp_path, self.output_file)
            self.logger.info(f"Saved batch of {len(batch)} items → {self.output_file} (total {len(all_rows)})")

        except Exception as e:
            self.logger.error(f"Save failed: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── Webdriver Lifecycle ───────────────────────────────────────────────────
    def _initialize_driver(self) -> webdriver.Chrome:
        self._cleanup()

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
                self.driver = webdriver.Chrome(options=opts)
                self.driver.set_page_load_timeout(25)
                self.driver.set_script_timeout(25)
                self.logger.info("Selenium Chrome driver successfully initialized")
                return self.driver
            except Exception as e:
                self.logger.error(f"Driver init attempt {attempt}/3 failed: {e}")
                if attempt == 3:
                    raise
                time.sleep(5)

    def _cleanup(self):
        if self.driver:
            self.logger.info("Closing active Chrome driver instance...")
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error during Chrome driver exit: {e}")
            self.driver = None

    # ── Link extraction ───────────────────────────────────────────────────────
    def _get_listing_urls(self, min_price: int, max_price: int, page: int) -> List[str]:
        """Fetch search results page and extract individual ad links using requests."""
        base_url = 'https://www.olx.uz/transport/legkovye-avtomobili/'
        page_param = "" if page == 1 else f"&page={page}"
        url = f"{base_url}?currency=UYE{page_param}&search%5Bfilter_float_price%3Afrom%5D={min_price}&search%5Bfilter_float_price%3Ato%5D={max_price}&search%5Border%5D=filter_float_price%3Adesc"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'lxml')
            # Extract links matching OLX's listing container class
            elements = soup.find_all(class_='css-1tqlkj0')
            links = []
            for el in elements[::2]:  # Skip duplicate elements rendered by OLX
                href = el.get('href')
                if href:
                    complete_url = "https://olx.uz" + href.split("#")[0]
                    links.append(complete_url)

            # Check redirection or pagination end
            if not links:
                return []

            return list(dict.fromkeys(links))  # preserves order deduplication

        except Exception as e:
            self.logger.warning(f"Error extracting listing links for {min_price}-{max_price} (page {page}): {e}")
            return []

    # ── Detail page parser & fallbacks ────────────────────────────────────────
    def _fallback_price(self, soup: BeautifulSoup) -> tuple:
        el = soup.find(attrs={"data-testid": "ad-price-container"})
        if not el:
            el = soup.find(attrs={"data-cy": "ad-price"})
        if el:
            text = el.get_text(strip=True)
            return extract_numeric(text), extract_currency(text)

        pattern = re.compile(r"[\d\s,.]{4,}.*(?:USD|\$|сум|у\.е\.)", re.IGNORECASE)
        for tag in soup.find_all(["h3", "strong", "span", "div"]):
            text = tag.get_text(strip=True)
            if pattern.search(text) and len(text) < 50:
                return extract_numeric(text), extract_currency(text)
        return None, None

    def _fallback_description(self, soup: BeautifulSoup) -> Optional[str]:
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

    def _fallback_location(self, soup: BeautifulSoup) -> tuple:
        region, district = None, None
        el = soup.find(attrs={"data-testid": "map-aside-section"})
        if el:
            texts = [p.get_text(strip=True) for p in el.find_all("p") if p.get_text(strip=True) != "Местоположение"]
            if len(texts) >= 2:
                district = clean_location(texts[0])
                region = translate(clean_location(texts[1]), "regions")
            elif len(texts) == 1:
                region = translate(clean_location(texts[0]), "regions")
        return region, district

    def _fallback_posting_date(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.find(attrs={"data-testid": "ad-posted-at"})
        if el:
            return format_date(el.get_text(strip=True))
        return None

    def _fallback_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        for attrs in (
            {"property": "og:image"},
            {"property": "og:image:url"},
            {"name": "twitter:image"},
            {"name": "twitter:image:src"},
        ):
            el = soup.find("meta", attrs=attrs)
            if el:
                image_url = self._normalize_image_url(el.get("content"))
                if image_url:
                    return image_url

        for el in soup.find_all(["img", "source", "link"]):
            for attr in ("src", "srcset", "data-src", "href", "imagesrcset"):
                value = el.get(attr)
                if not value:
                    continue
                for candidate in str(value).split(","):
                    image_url = self._normalize_image_url(candidate.strip().split(" ")[0])
                    if image_url:
                        return image_url

        match = IMAGE_URL_RE.search(str(soup))
        return self._normalize_image_url(match.group(0)) if match else None

    def _fallback_seller_type(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in (
            '[data-testid*="seller"]',
            '[data-testid*="user"]',
            '[data-cy*="seller"]',
            '[data-cy*="user"]',
        ):
            for el in soup.select(selector):
                seller_type = self._normalize_seller_type(el.get_text(" ", strip=True))
                if seller_type:
                    return seller_type
        return self._normalize_seller_type(soup.get_text(" ", strip=True))

    def _fallback_params(self, soup: BeautifulSoup) -> dict:
        result = {}
        container = soup.find(attrs={"data-testid": "ad-parameters-container"})
        if not container:
            return result

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
                seller_type = self._normalize_seller_type(text)
                if seller_type:
                    result["seller_type"] = seller_type

        return result

    def _normalize_seller_type(self, value: str) -> Optional[str]:
        if not value:
            return None
        normalized = re.sub(r"\s+", " ", value).strip().lower()
        if normalized in SELLER_MAP:
            return SELLER_MAP[normalized]
        if "частное лицо" in normalized or "jismoniy shaxs" in normalized:
            return "private"
        if "бизнес" in normalized or "biznes" in normalized:
            return "business"
        return None

    def _normalize_image_url(self, value: Any) -> Optional[str]:
        if not isinstance(value, str) or not value:
            return None

        value = value.strip()
        if value.startswith("//"):
            value = "https:" + value
        if not value.startswith(("http://", "https://")):
            match = IMAGE_URL_RE.search(value)
            value = match.group(0) if match else value

        if "olxcdn.com" not in value or value.startswith("data:"):
            return None

        return (
            value.replace("{width}", "800")
            .replace("{height}", "600")
            .replace("&amp;", "&")
        )

    def _find_first_image_url(self, obj: Any) -> Optional[str]:
        if isinstance(obj, str):
            return self._normalize_image_url(obj)
        if isinstance(obj, list):
            for item in obj:
                url = self._find_first_image_url(item)
                if url:
                    return url
        if isinstance(obj, dict):
            preferred_keys = (
                "link", "url", "src", "href", "imageUrl", "image_url",
                "original", "large", "medium", "small", "thumbnail",
            )
            for key in preferred_keys:
                if key in obj:
                    url = self._find_first_image_url(obj[key])
                    if url:
                        return url
            for value in obj.values():
                url = self._find_first_image_url(value)
                if url:
                    return url
        return None

    def _is_inactive_page(self, soup: BeautifulSoup) -> bool:
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

    def _parse_next_data(self, data: dict) -> dict:
        result = {}
        try:
            ad = data["props"]["pageProps"]["ad"]
        except (KeyError, TypeError):
            return result

        # --- price ---
        price_block = ad.get("price") or {}
        raw_price = price_block.get("value")
        result["price"] = extract_numeric(str(raw_price)) if raw_price else None
        result["currency"] = price_block.get("currency") or None

        # --- description ---
        desc = (ad.get("description") or "").strip()
        result["description"] = desc[:2000] if desc else None

        # --- params list ---
        for param in ad.get("params") or []:
            key = (param.get("key") or "").lower()
            field = PARAM_KEY_MAP.get(key)
            if not field:
                continue
            value_obj = param.get("value") or {}
            label = (value_obj.get("label") or "").strip()
            if not label:
                label = str(value_obj.get("key") or "").strip()
            if not label:
                continue
            cat = LABEL_CATEGORY.get(field)
            if field == "seller_type":
                result[field] = self._normalize_seller_type(label) or translate(label, cat) or label
            else:
                result[field] = translate(label, cat) if cat else label

        # --- advertiser type (alternative location) ---
        if "seller_type" not in result:
            adv = ad.get("advertiser") or {}
            for key in ("accountType", "account_type", "type", "userType", "user_type"):
                seller_type = self._normalize_seller_type(str(adv.get(key) or ""))
                if seller_type:
                    result["seller_type"] = seller_type
                    break

        # --- location ---
        loc = ad.get("location") or {}
        region_raw = (loc.get("region") or {}).get("name") or ""
        district_raw = (loc.get("district") or {}).get("name") or \
                       (loc.get("city") or {}).get("name") or ""
        result["region"] = translate(region_raw.strip(), "regions") if region_raw else None
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
            image_url = self._find_first_image_url(ad.get(key))
            if image_url:
                result["image_url"] = image_url
                break

        return result

    def _parse_detail(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """Loads detail page source in Chrome and extracts structured listing info."""
        for attempt in range(1, max_retries + 2):
            try:
                self.driver.delete_all_cookies()
                self.driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except TimeoutException:
                self.logger.warning(f"Timeout loading detail page: {url} (attempt {attempt})")
                if attempt > max_retries:
                    return None
                time.sleep(3)
                continue
            except WebDriverException as e:
                err = str(e).lower()
                if "no such window" in err or "invalid session" in err:
                    self.logger.warning("WebDriver session lost — reinitializing Chrome")
                    self._initialize_driver()
                if attempt > max_retries:
                    return None
                time.sleep(3)
                continue

            try:
                soup = BeautifulSoup(self.driver.page_source, "lxml")
            except Exception:
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Check deleted/inactive ad
            if self._is_inactive_page(soup):
                raise InactiveAdError(url)

            car = {}
            # Step 1: __NEXT_DATA__
            next_script = soup.find("script", id="__NEXT_DATA__")
            if next_script:
                try:
                    ndata = json.loads(next_script.string or "")
                    car = self._parse_next_data(ndata)
                except Exception as e:
                    self.logger.warning(f"Error parsing __NEXT_DATA__ JSON: {e}")

            # Step 2: Gaps fill fallback
            if not car.get("price"):
                p, c = self._fallback_price(soup)
                car["price"], car["currency"] = p, c

            if not car.get("description"):
                car["description"] = self._fallback_description(soup)

            if not car.get("region"):
                r, d = self._fallback_location(soup)
                car.setdefault("region", r)
                car.setdefault("district", d)

            if not car.get("posting_date"):
                car["posting_date"] = self._fallback_posting_date(soup)

            if not car.get("image_url"):
                car["image_url"] = self._fallback_image_url(soup)

            if not car.get("seller_type"):
                car["seller_type"] = self._fallback_seller_type(soup)

            html_params = self._fallback_params(soup)
            for field, val in html_params.items():
                if not car.get(field):
                    car[field] = val

            # Extract ad_id
            m = re.search(r"-ID([a-zA-Z0-9]+)\.html", url)
            ad_id = m.group(1) if m else None

            # Build standardized final record
            record = {col: None for col in self.columns}
            record.update({
                "ad_id": ad_id,
                "url": url,
                "posting_date": car.get("posting_date"),
                "region": car.get("region"),
                "district": car.get("district"),
                "price": car.get("price"),
                "currency": car.get("currency"),
                "description": car.get("description"),
                "image_url": car.get("image_url"),
                "seller_type": car.get("seller_type"),
                "model": car.get("model"),
                "body_type": car.get("body_type"),
                "sale_type": car.get("sale_type"),
                "year": car.get("year"),
                "mileage": car.get("mileage"),
                "transmission": car.get("transmission"),
                "color": car.get("color"),
                "engine_volume": car.get("engine_volume"),
                "fuel_type": car.get("fuel_type"),
                "condition": car.get("condition"),
                "owners_count": car.get("owners_count"),
                "additional_options": car.get("additional_options"),
                "source": "olx",
            })

            return record

        return None

    # ── Main Run Loop ─────────────────────────────────────────────────────────
    def run(self, max_pages_per_range: int = 50, test_limit: Optional[int] = None):
        self.logger.info("=" * 60)
        self.logger.info("Unified OLX.uz Scraper Started")
        if test_limit:
            self.logger.info(f"TEST MODE — will stop after {test_limit} new listings")
        self.logger.info("=" * 60)

        # Load adaptive price ranges from ranges file or static fallback list
        ranges_file = os.path.join(os.path.dirname(__file__), "data", "olx_price_ranges.json")
        price_ranges = DEFAULT_PRICE_RANGES
        if os.path.exists(ranges_file):
            try:
                with open(ranges_file, "r") as f:
                    ranges_data = json.load(f)
                price_ranges = ranges_data["price_ranges"]
                self.logger.info(f"Loaded {len(price_ranges)} adaptive price ranges from {ranges_file}")
            except Exception as e:
                self.logger.error(f"Could not load price ranges file: {e}. Falling back to default list.")

        # Initialize selenium browser
        self._initialize_driver()

        total_new = 0
        consecutive_fails = 0
        processed_since_restart = 0
        batch: List[Dict] = []

        total_ranges = len(price_ranges)
        for idx, (min_price, max_price) in enumerate(price_ranges, 1):
            if self._shutdown:
                break

            self.logger.info(f"Processing price range {idx}/{total_ranges}: {min_price} to {max_price} USD")

            page_num = 1
            consecutive_no_new_links = 0

            while page_num <= max_pages_per_range:
                if self._shutdown:
                    break

                if test_limit and total_new >= test_limit:
                    break

                self.logger.info(f"Checking search result page {page_num} for range {min_price}-{max_price}")
                links = self._get_listing_urls(min_price, max_price, page_num)

                if not links:
                    self.logger.info("No links found on this page. Moving to next price range.")
                    break

                new_links_in_page = 0
                for link in links:
                    if self._shutdown:
                        break

                    if test_limit and total_new >= test_limit:
                        break

                    # Deduplication
                    if link in self.seen_ids:
                        continue
                    if link in self.inactive_urls:
                        continue

                    new_links_in_page += 1

                    # Browser maintenance and recovery routines
                    if consecutive_fails >= 8:
                        self.logger.warning("Too many continuous parse failures — performing browser hard restart")
                        self._initialize_driver()
                        consecutive_fails = 0
                        processed_since_restart = 0
                        time.sleep(10)
                    elif processed_since_restart >= 80:
                        self.logger.info("Performing browser routine memory refresh...")
                        self._initialize_driver()
                        processed_since_restart = 0
                        time.sleep(3)

                    # Keep driver alive safety check
                    try:
                        _ = self.driver.current_url
                    except Exception:
                        self.logger.warning("Selenium connection lost — restoring driver")
                        self._initialize_driver()

                    self.logger.info(f"Scraping detail page: {link.split('/')[-1]}")
                    try:
                        record = self._parse_detail(link)
                        if record:
                            batch.append(record)
                            self.seen_ids.add(link)
                            total_new += 1
                            consecutive_fails = 0
                            processed_since_restart += 1

                            # Save batch incrementally to prevent loss
                            if len(batch) >= cfg.BATCH_SIZE:
                                self._save(batch)
                                batch.clear()
                        else:
                            consecutive_fails += 1
                    except InactiveAdError:
                        self.inactive_urls.add(link)
                        self.logger.info(f"Listing is inactive/deleted — skipping: {link}")
                        consecutive_fails = 0
                    except Exception as e:
                        self.logger.error(f"Failed parsing listing detail {link}: {e}")
                        consecutive_fails += 1

                    # Sleep between item details requests
                    time.sleep(random.uniform(cfg.DEFAULT_DELAY[0], cfg.DEFAULT_DELAY[1]))

                if new_links_in_page == 0:
                    consecutive_no_new_links += 1
                    if consecutive_no_new_links >= 2:
                        self.logger.info("End of unique pagination results reached for this price range.")
                        break
                else:
                    consecutive_no_new_links = 0

                page_num += 1
                time.sleep(2.0)  # brief pause between paginating search index

            if test_limit and total_new >= test_limit:
                self.logger.info(f"Target test limit of {test_limit} records reached. Stopping scraper.")
                break

        # Flush leftover records in buffer
        if batch:
            self._save(batch)
            batch.clear()

        # Teardown Chrome
        self._cleanup()
        self.logger.info(f"OLX Scraper finished successfully. Scraped {total_new} new listing records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified OLX.uz car scraper")
    parser.add_argument(
        "--test", type=int, default=None, metavar="N",
        help="Quick-test mode: stop after N new records",
    )
    parser.add_argument(
        "--output", default="scraper/data/olx_car_data.csv",
        help="Output CSV file path (default: scraper/data/olx_car_data.csv)",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "..", args.output) if args.output.startswith("scraper/") else args.output
    output_path = os.path.abspath(output_path)

    # For testing, run on a separate test output file
    if args.test and output_path.endswith("olx_car_data.csv"):
        output_path = output_path.replace("olx_car_data.csv", "olx_car_data_test.csv")

    scraper = OlxScraper(output_file=output_path)
    scraper.run(test_limit=args.test)
