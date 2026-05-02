"""
Car Scraper Module

This module scrapes detailed car information from OLX.uz car advertisement pages.
It uses Selenium WebDriver to handle JavaScript-rendered content and extracts
comprehensive car data including:

- Basic Information: URL, posting date, price, currency, description, image URL
- Location: Region and district
- Car Details: Model, body type, year, mileage, transmission, color, engine volume,
  fuel type, condition, number of owners, additional options
- Seller Information: Seller type (private/dealer)

The scraper includes robust error handling with retry logic, timeout management,
and automatic browser session recovery. It processes car links from a JSON file
and saves scraped data incrementally to prevent data loss.

Features:
- Automatic retry on failures with configurable max retries
- Timeout detection and browser session recovery
- Translation support for Russian/Uzbek text to English
- Deleted ad detection and tracking
- Incremental saving to prevent data loss
- Graceful shutdown handling with cleanup

Usage:
    python car_scraper.py

The script expects 'car_links.json' in the same directory and outputs
to 'car_data.json' by default.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
import logging
import os
from requests.exceptions import RequestException, HTTPError
import random
from datetime import datetime
import re
from dateutil import parser
import locale
import lxml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import subprocess
import tempfile
import platform
import signal
import atexit
# Set shorter timeouts for requests
import urllib3
urllib3.util.timeout.Timeout.DEFAULT_TIMEOUT = 20.0  # Reduce default timeout to 20 seconds

# Suppress TensorFlow logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable for the driver
driver = None

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal. Cleaning up...")
    cleanup()
    exit(0)

def cleanup():
    """Clean up resources"""
    global driver
    if driver:
        logger.info("Closing Chrome driver...")
        try:
            driver.quit()
            driver = None
        except Exception as e:
            logger.error(f"Error closing driver: {e}")
            # Try to forcefully kill any remaining Chrome processes if on Linux/Mac
            if platform.system() != "Windows":
                try:
                    subprocess.run(["pkill", "-f", "chrome"], check=False)
                except Exception as err:
                    logger.error(f"Failed to kill Chrome processes: {err}")
        logger.info("Chrome driver closed successfully")

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# Cyrillic to Latin mapping
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

def convert_to_latin(text: str) -> str:
    """
    Convert Cyrillic text to Latin
    """
    if not text:
        return None
    return ''.join(CYRILLIC_TO_LATIN.get(c, c) for c in text)

def load_translations() -> Dict:
    """
    Load translations from JSON file
    """
    try:
        with open('translations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")
        return {}

def translate_value(value: str, translations: Dict, category: str) -> str:
    """
    Translate a value using the translations dictionary
    """
    if not value or not translations or category not in translations:
        return value
    
    # For additional options, split by comma and translate each option
    if category == 'additional_options' and value:
        options = [opt.strip() for opt in value.split(',')]
        translated_options = []
        for opt in options:
            if opt in translations[category]:
                translated_options.append(translations[category][opt])
            else:
                translated_options.append(opt)
        return ', '.join(translated_options)
    
    # For other categories, direct translation
    return translations[category].get(value, value)

def extract_numeric_value(text: str) -> str:
    """
    Extract numeric value from text
    """
    if not text:
        return None
    # Remove all non-digit characters except decimal point
    numeric = re.sub(r'[^\d.]', '', text)
    return numeric if numeric else None

def extract_currency(text: str) -> str:
    """
    Extract currency from price text
    """
    if not text:
        return None
    # Look for common currency symbols
    if '$' in text:
        return 'USD'
    elif '€' in text:
        return 'EUR'
    elif '₽' in text:
        return 'RUB'
    elif 'сум' in text.lower():
        return 'UZS'
    return None

def format_date(date_str: str) -> str:
    """
    Convert date string to DD.MM.YYYY format using dateutil parser
    """
    try:
        # Remove the 'г.' suffix if present
        date_str = date_str.replace(' г.', '')
        
        # Map of Russian month names to numbers
        month_map = {
            'января': '01', 'февраля': '02', 'марта': '03',
            'апреля': '04', 'мая': '05', 'июня': '06',
            'июля': '07', 'августа': '08', 'сентября': '09',
            'октября': '10', 'ноября': '11', 'декабря': '12'
        }
        
        # Extract day, month, and year
        parts = date_str.split()
        if len(parts) == 3:
            day = parts[0]
            month = month_map.get(parts[1].lower(), '01')  # Default to January if month not found
            year = parts[2]
            
            # Create date string in YYYY-MM-DD format
            date_str = f"{year}-{month}-{day}"
            
            # Parse and format
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d.%m.%Y")
        else:
            raise ValueError(f"Unexpected date format: {date_str}")
            
    except Exception as e:
        logger.error(f"Error formatting date {date_str}: {str(e)}")
        return date_str

def clean_location_text(text: str) -> str:
    """
    Remove commas and periods from location text
    """
    if not text:
        return None
    return text.replace(',', '').replace('.', '').strip()

def save_deleted_ad(url: str):
    """
    Save a deleted ad URL to a file
    """
    try:
        # Create the file if it doesn't exist
        if not os.path.exists('deleted_ads.json'):
            with open('deleted_ads.json', 'w', encoding='utf-8') as f:
                json.dump({'deleted_ads': []}, f, ensure_ascii=False, indent=2)
        
        # Load existing deleted ads
        with open('deleted_ads.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add the new URL if it's not already in the list
        if url not in data['deleted_ads']:
            data['deleted_ads'].append(url)
            
            # Save back to file
            with open('deleted_ads.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved deleted ad URL: {url}")
    except Exception as e:
        logger.error(f"Error saving deleted ad URL {url}: {str(e)}")

def get_random_user_agent():
    """
    Return a random user agent from a predefined list
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

def initialize_driver():
    """Initialize Chrome driver with appropriate settings for the current platform"""
    global driver
    
    # First, make sure any existing driver is properly closed
    cleanup()
    
    chrome_options = Options()
    
    # Platform specific settings
    system = platform.system()
    if system == "Darwin":  # macOS
        # For MacOS, don't use headless mode and enable visible browser
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
    else:  # Linux/Windows
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
    
    # SSL and security options
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--allow-insecure-localhost')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--reduce-security-for-testing')
    chrome_options.add_argument('--allow-running-insecure-content')
    
    # Performance and stability options
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--enable-unsafe-swiftshader')
    chrome_options.add_argument('--disable-application-cache')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--js-flags=--max_old_space_size=512')
    
    # Set a standard user agent
    standard_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    chrome_options.add_argument(f'--user-agent={standard_user_agent}')
    
    # Additional preferences
    prefs = {
        'profile.default_content_setting_values.notifications': 2,
        'disk-cache-size': 52428800,  # 50MB cache
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 1,  # Enable images
        'profile.default_content_setting_values.cookies': 1,  # Enable cookies
        'profile.default_content_setting_values.javascript': 1,  # Enable JavaScript
        'profile.default_content_setting_values.plugins': 1,  # Enable plugins
        'profile.default_content_setting_values.media_stream': 1,  # Enable media
        'profile.default_content_setting_values.geolocation': 1,  # Enable geolocation
        'profile.default_content_setting_values.auto_select_certificate': 1,  # Enable auto-select certificate
        'profile.default_content_setting_values.mixed_script': 1,  # Enable mixed script
        'profile.default_content_setting_values.media_stream_mic': 1,  # Enable microphone
        'profile.default_content_setting_values.media_stream_camera': 1,  # Enable camera
        'profile.default_content_setting_values.protocol_handlers': 1,  # Enable protocol handlers
        'profile.default_content_setting_values.midi_sysex': 1,  # Enable MIDI
        'profile.default_content_setting_values.push_messaging': 1,  # Enable push messaging
        'profile.default_content_setting_values.ssl_cert_decisions': 1,  # Enable SSL cert decisions
        'profile.default_content_setting_values.metro_switch_to_desktop': 1,  # Enable metro switch
        'profile.default_content_setting_values.protected_media_identifier': 1,  # Enable protected media
        'profile.default_content_setting_values.site_engagement': 1,  # Enable site engagement
        'profile.default_content_setting_values.durable_storage': 1,  # Enable durable storage
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    # Set up retry mechanism for driver initialization
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            # Set shorter timeouts
            driver.set_page_load_timeout(20)  # Reduced from 30 to 20 seconds
            driver.set_script_timeout(20)     # Reduced from 30 to 20 seconds
            
            # Test the connection
            try:
                driver.get("https://www.google.com")
                logger.info("Chrome driver initialized successfully")
                return driver
            except Exception as e:
                logger.error(f"Connection test failed: {str(e)}")
                raise
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Failed to initialize Chrome driver (attempt {retry_count}/{max_retries}): {e}")
            if retry_count >= max_retries:
                logger.error("Max retries reached for driver initialization")
                raise
            time.sleep(5)  # Wait before retry

def get_car_info(url: str, driver: webdriver.Chrome, max_retries: int = 3) -> Dict:
    """
    Scrape car information from a single URL with retry logic.
    """
    retry_count = 0
    translations = load_translations()
    
    while retry_count <= max_retries:
        try:
            # Load page with Selenium
            logger.info(f"Loading page with Selenium: {url}")
            
            # Try to load the page with error handling
            try:
                # Clear cookies and cache before each attempt
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
                
                # Set a shorter page load timeout
                driver.set_page_load_timeout(25)  # Reduced from 60 to 25 seconds
                
                # Load the page
                driver.get(url)
                
                # Wait for the page to be minimally interactive
                wait = WebDriverWait(driver, 10)  # Reduced from 20 to 10 seconds
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
            except TimeoutException as e:
                logger.error(f"Timeout loading page: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"Retrying due to timeout... (Attempt {retry_count}/{max_retries})")
                    time.sleep(3)  # Reduced from 5 to 3 seconds wait before retry
                    continue
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"Retrying due to page load error... (Attempt {retry_count}/{max_retries})")
                    time.sleep(3)  # Reduced from 5 to 3 seconds wait before retry
                    continue
                else:
                    return None
            
            # Quick check for page validity
            try:
                # Check if we have an error page or deleted ad
                error_indicators = ["страница не найдена", "объявление не найдено", "404", "deleted", "removed"]
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                if any(indicator in page_text for indicator in error_indicators):
                    logger.warning(f"Page appears to be an error page or deleted ad: {url}")
                    save_deleted_ad(url)
                    return None
                
                # Try to find key elements
                try:
                    wait = WebDriverWait(driver, 4)  # Reduced from 10 to 8 seconds
                    element = wait.until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, '[data-testid="ad-parameters-container"], [data-testid="map-aside-section"], h3.css-fqcbii'
                        ))
                    )
                    logger.info("Page content loaded successfully")
                except TimeoutException:
                    logger.warning("Specific elements not found after 8s, proceeding with parsing")
                
            except Exception as e:
                logger.error(f"Error checking page validity: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    continue
                else:
                    return None
            
            # Get the page source after confirming content is loaded
            try:
                page_source = driver.page_source
            except Exception as e:
                logger.error(f"Error getting page source: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    continue
                else:
                    return None
                
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Parse the data
            params_container = soup.find('div', {'data-testid': 'ad-parameters-container'})
            if not params_container:
                logger.warning(f"Could not find parameters container for {url}")
                # Check if this might be a deleted ad or different page format
                title_element = soup.find(['h1', 'h2', 'h3'], class_=lambda c: c and ('title' in c.lower() or 'heading' in c.lower()))
                if title_element and any(term in title_element.get_text().lower() for term in ["удалено", "не найдено", "removed", "deleted"]):
                    logger.info(f"Ad appears to be deleted: {url}")
                    save_deleted_ad(url)
                return None
            
            # Get location information
            region = None
            district = None
            
            location_container = soup.find('div', {'data-testid': 'map-aside-section'})
            if location_container:
                inner_container = location_container.find('div', class_='css-1q7h1ph')
                if inner_container:
                    location_texts = inner_container.find_all('p')
                    
                    if len(location_texts) > 1:
                        for text_element in location_texts:
                            text = text_element.get_text(strip=True)
                            
                            if text == "Местоположение":
                                continue
                                
                            cleaned_text = clean_location_text(text)
                            if cleaned_text:
                                if not district:
                                    district = cleaned_text
                                    translated_district = translate_value(district, translations, 'districts')
                                    if translated_district == district:
                                        district = convert_to_latin(district)
                                    else:
                                        district = translated_district
                                elif not region:
                                    region = cleaned_text
                                    region = translate_value(region, translations, 'regions')
            
            # Get price
            price_element = soup.find('h3', class_='css-fqcbii')
            price_text = price_element.get_text(strip=True) if price_element else None
            price = extract_numeric_value(price_text) if price_text else None
            currency = extract_currency(price_text) if price_text else None
            
            # Get description
            description_element = soup.find('div', class_='css-19duwlz')
            description = description_element.get_text() if description_element else None
            
            # Get main image URL
            image_element = soup.find('img', {'data-testid': 'swiper-image'})
            image_url = image_element.get('src') if image_element else None
            
            # Get posting date
            posting_date_element = soup.find('span', {'data-testid': 'ad-posted-at'})
            posting_date = None
            if posting_date_element:
                date_text = posting_date_element.get_text(strip=True)
                # Convert date text to standard format
                posting_date = format_date(date_text)
                logger.info(f"Found posting date: {posting_date}")
            
            # Initialize car info dictionary
            car_info = {
                'url': url,
                'posting_date': posting_date,
                'region': region,
                'district': district,
                'price': price,
                'currency': currency,
                'description': description,
                'image_url': image_url,
                'seller_type': None,
                'model': None,
                'body_type': None,
                'sale_type': None,
                'year': None,
                'mileage': None,
                'transmission': None,
                'color': None,
                'engine_volume': None,
                'fuel_type': None,
                'condition': None,
                'owners_count': None,
                'additional_options': None
            }
            
            # Extract all parameters
            for p in params_container.find_all('p', class_='css-1los5bp'):
                text = p.get_text(strip=True)
                
                if 'Частное лицо' in text:
                    car_info['seller_type'] = 'private'
                elif 'Модель' in text:
                    car_info['model'] = text.replace('Модель', '').strip()
                elif 'Тип кузова' in text:
                    value = text.replace('Тип кузова:', '').strip()
                    car_info['body_type'] = translate_value(value, translations, 'body_type')
                elif 'Условия продажи' in text:
                    value = text.replace('Условия продажи:', '').strip()
                    car_info['sale_type'] = translate_value(value, translations, 'sale_type')
                elif 'Год выпуска' in text:
                    car_info['year'] = text.replace('Год выпуска:', '').strip()
                elif 'Пробег' in text:
                    value = text.replace('Пробег:', '').strip()
                    car_info['mileage'] = extract_numeric_value(value)
                elif 'Коробка передач' in text:
                    value = text.replace('Коробка передач:', '').strip()
                    car_info['transmission'] = translate_value(value, translations, 'transmission')
                elif 'Цвет' in text:
                    value = text.replace('Цвет:', '').strip()
                    car_info['color'] = translate_value(value, translations, 'color')
                elif 'Объем двигателя' in text:
                    value = text.replace('Объем двигателя:', '').strip()
                    car_info['engine_volume'] = extract_numeric_value(value)
                elif 'Вид топлива' in text:
                    value = text.replace('Вид топлива:', '').strip()
                    car_info['fuel_type'] = translate_value(value, translations, 'fuel_type')
                elif 'Состояние машины' in text:
                    value = text.replace('Состояние машины:', '').strip()
                    car_info['condition'] = translate_value(value, translations, 'condition')
                elif 'Количество хозяев' in text:
                    car_info['owners_count'] = text.replace('Количество хозяев:', '').strip()
                elif 'Доп. опции' in text:
                    value = text.replace('Доп. опции:', '').strip()
                    car_info['additional_options'] = translate_value(value, translations, 'additional_options')
            
            return car_info
            
        except TimeoutException as e:
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"Timeout error on {url}: {str(e)}")
                logger.warning(f"Retrying... (Attempt {retry_count}/{max_retries})")
                try:
                    driver.refresh()
                except:
                    pass
                continue
            else:
                logger.warning(f"Timeout persists after {max_retries} retry, skipping URL: {url}")
                return None
                
        except WebDriverException as e:
            # Check for critical driver errors
            if "no such window" in str(e).lower() or "invalid session id" in str(e).lower():
                logger.warning(f"Browser window closed or invalid session. Reinitializing Chrome driver...")
                try:
                    driver.quit()
                except:
                    pass
                driver = initialize_driver()
                retry_count += 1
                if retry_count <= max_retries:
                    continue
                else:
                    logger.warning(f"Driver issues persist after {max_retries} retry, skipping URL: {url}")
                    return None
            
            # Other WebDriver errors
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"WebDriver error on {url}: {str(e)}")
                logger.warning(f"Retrying... (Attempt {retry_count}/{max_retries})")
                continue
            else:
                logger.warning(f"WebDriver error persists after {max_retries} retry, skipping URL: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {str(e)}")
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"Retrying... (Attempt {retry_count}/{max_retries})")
                continue
            else:
                logger.warning(f"Error persists after {max_retries} retry, skipping URL: {url}")
                return None
    
    logger.error(f"Failed to process {url} after {max_retries} attempts")
    return None

def load_car_links(json_file: str) -> List[str]:
    """
    Load car links from a JSON file
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'links' in data:
                return data['links']
            elif isinstance(data, list):
                return data
            else:
                logger.error(f"Unexpected JSON structure in {json_file}")
                return []
    except Exception as e:
        logger.error(f"Error loading car links from {json_file}: {str(e)}")
        return []

def load_existing_data(output_file: str) -> List[Dict]:
    """
    Load existing car data from the output file
    """
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading existing data from {output_file}: {str(e)}")
    return []

def process_car_links(links: List[str], output_file: str = 'car_data.json'):
    """Process list of car links and save data to JSON file"""
    global driver
    
    try:
        # Load existing data
        existing_data = load_existing_data(output_file)
        processed_urls = {item['url'] for item in existing_data}
        
        # Initialize the driver
        driver = initialize_driver()
        consecutive_timeouts = 0
        processed_since_restart = 0
        max_consecutive_timeouts = 10  # Reduced from 5 to 3
        
        # Process each URL directly with Selenium
        for i, link in enumerate(links, 1):
            if link in processed_urls:
                logger.info(f"Skipping already processed car {i}/{len(links)}: {link}")
                continue
            
            # Check if we've had too many consecutive timeouts
            if consecutive_timeouts >= max_consecutive_timeouts:
                logger.warning(f"Too many consecutive timeouts ({consecutive_timeouts}). Recreating WebDriver...")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(3)  # Reduced from 5 to 3 seconds wait before recreating driver
                driver = initialize_driver()
                consecutive_timeouts = 0
                processed_since_restart = 0
                # Add a shorter pause to avoid rate limiting
                logger.info("Pausing for 15 seconds to avoid rate limiting...")
                time.sleep(15)  # Reduced from 30 to 15 seconds
            
            # Periodic browser refresh to avoid memory issues
            elif processed_since_restart >= 100:  # Reduced from 50 to 30
                logger.info("Performing routine browser refresh after 30 processed items")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(3)  # Reduced from 5 to 3 seconds wait before recreating driver
                driver = initialize_driver()
                processed_since_restart = 0
                time.sleep(3)  # Reduced from 5 to 3 seconds short pause after browser refresh
            
            # Process the car directly with Selenium
            logger.info(f"Processing car {i}/{len(links)}: {link}")
            try:
                # Verify WebDriver is still responsive
                try:
                    driver.current_url
                except Exception as e:
                    logger.error(f"WebDriver not responsive: {str(e)}")
                    driver = initialize_driver()
                    time.sleep(3)  # Reduced from 5 to 3 seconds
                
                car_info = get_car_info(link, driver)
                
                if car_info:
                    try:
                        car_info['url'] = link
                        existing_data.append(car_info)
                        
                        # Save after each successful scrape
                        try:
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                            logger.info(f"Successfully saved data for car {i}: {link}")
                        except Exception as save_error:
                            logger.error(f"Error saving data to file for car {i}: {str(save_error)}")
                            # Try to save to a backup file
                            backup_file = f"{output_file}.backup"
                            try:
                                with open(backup_file, 'w', encoding='utf-8') as f:
                                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                                logger.info(f"Saved backup data to {backup_file}")
                            except Exception as backup_error:
                                logger.error(f"Failed to save backup data: {str(backup_error)}")
                        
                        # Reset timeout counter on success
                        consecutive_timeouts = 0
                        processed_since_restart += 1
                    except Exception as data_error:
                        logger.error(f"Error processing data for car {i}: {str(data_error)}")
                        consecutive_timeouts += 1
                else:
                    # Increment timeout counter if get_car_info returned None
                    logger.warning(f"No data retrieved for car {i}: {link}")
                    consecutive_timeouts += 1
                
                # Add a small random delay between requests to avoid detection
                time.sleep(random.uniform(1.0, 2.0))  # Reduced from 2.0-4.0 to 1.0-2.0 seconds
                
            except Exception as e:
                logger.error(f"Error processing {link}: {str(e)}")
                consecutive_timeouts += 1
                # If we get a WebDriver error, recreate the driver
                if "WebDriver" in str(e) or "timeout" in str(e).lower():
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(3)  # Reduced from 5 to 3 seconds
                    driver = initialize_driver()
                continue
                
    except Exception as e:
        logger.error(f"Fatal error in process_car_links: {str(e)}")
        raise
        
    finally:
        cleanup()

if __name__ == "__main__":
    try:
        # Load car links
        car_links = load_car_links('car_links.json')
        logger.info(f"Loaded {len(car_links)} car links from car_links.json")
        
        # Process car links
        # Save output to the main dataset to avoid duplicating already scraped cars
        process_car_links(car_links, output_file='data/Prepared/car_data.json')
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise
    finally:
        cleanup() 