"""
Car Links Cleaner Module

This module checks car advertisement links to identify which ones are active
and which have been deleted or are no longer available. It processes links
from a JSON file and categorizes them into active and inactive lists.

The module uses parallel processing with ThreadPoolExecutor to efficiently
check multiple links simultaneously. It detects inactive ads by:

- HTTP status codes (404, 410)
- Specific HTML elements indicating deleted ads
- Error messages in page content

Features:
- Multi-threaded processing for faster link checking
- Progress tracking with tqdm progress bar
- Periodic saving of results to prevent data loss
- Graceful interruption handling (Ctrl+C)
- Rate limiting with random delays between requests
- Preserves original car_links.json file

The results are saved to:
- results/active_links.json: List of active advertisement URLs
- results/inactive_links.json: List of inactive/deleted advertisement URLs

Usage:
    python clean_car_links.py

The script expects 'car_links.json' in the same directory.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Create directories for results
os.makedirs('results', exist_ok=True)

# Global variables for handling interruptions
active_links = []
inactive_links = []
links_processed = 0
total_links = 0
save_interval = 100  # Save progress every 100 links

# Signal handler for graceful interruption
def signal_handler(sig, frame):
    logger.info(f"Received interrupt signal. Saving progress...")
    save_results()
    logger.info(f"Processed {links_processed}/{total_links} links before interruption.")
    logger.info(f"Found {len(inactive_links)} inactive links and {len(active_links)} active links.")
    exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def get_random_user_agent():
    """
    Return a random user agent from a predefined list
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

def load_car_links(json_file='car_links.json'):
    """Load car links from a JSON file"""
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

def save_results():
    """Save active and inactive links to separate JSON files"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Save active links
    active_file = f"results/active_links.json"
    try:
        with open(active_file, 'w', encoding='utf-8') as f:
            json.dump(active_links, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(active_links)} active links to {active_file}")
    except Exception as e:
        logger.error(f"Error saving active links: {str(e)}")
    
    # Save inactive links
    inactive_file = f"results/inactive_links.json"
    try:
        with open(inactive_file, 'w', encoding='utf-8') as f:
            json.dump(inactive_links, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(inactive_links)} inactive links to {inactive_file}")
    except Exception as e:
        logger.error(f"Error saving inactive links: {str(e)}")
    
    # Do NOT update the original car_links.json file

def is_inactive(url, timeout=5):
    """Check if a car ad is inactive"""
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Only consider 404/410 as definitive indicators
        if response.status_code in [404, 410]:
            logger.info(f"URL returned {response.status_code}: {url}")
            return True
            
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        
        # PRIMARY CHECK: Look for the specific inactive message div
        inactive_msg_div = soup.find('div', {'data-testid': 'ad-inactive-msg'})
        if inactive_msg_div:
            print(inactive_msg_div)
            # SECONDARY CHECK: If we found the div, look for the h4 with the specific message
            inactive_h4 = soup.find('h4', class_='css-3fj7ob')
            if inactive_h4 and 'Объявление больше не доступно' in inactive_h4.text:
                print(inactive_h4)
                logger.info(f"Found inactive message in h4: {url}")
                return True
            
            # Even without the h4, if we have the inactive div, it's likely inactive
            logger.info(f"Found inactive div but no message: {url}")
            return True
            
        # If we don't have the inactive div, the ad is probably active
        return False
        
    except Exception as e:
        logger.warning(f"Error checking {url}: {str(e)}")
        # If we can't check, we can't determine if it's inactive
        # The safest option is to return False to keep the link in the list
        return False

def check_link(idx, url):
    """Check a single link with proper delay"""
    time.sleep(random.uniform(0.5, 2))  # Random delay to avoid rate limiting
    inactive = is_inactive(url)
    return idx, url, inactive

def process_result(result, progress_bar):
    """Process the result of a link check and update progress"""
    global links_processed, active_links, inactive_links
    
    idx, url, inactive = result
    links_processed += 1
    
    if inactive:
        inactive_links.append(url)
        progress_bar.set_description(f"Found {len(inactive_links)} inactive, {len(active_links)} active")
    else:
        active_links.append(url)
    
    # Save progress periodically
    if links_processed % save_interval == 0:
        save_results()
        progress_bar.set_description(f"Saved progress: {links_processed}/{total_links} links")

def clean_car_links(input_file='car_links.json', max_workers=5):
    """
    Process car links to identify active and inactive ones
    """
    global active_links, inactive_links, links_processed, total_links
    
    # Reset global variables
    active_links = []
    inactive_links = []
    links_processed = 0
    
    # Load links
    links = load_car_links(input_file)
    total_links = len(links)
    logger.info(f"Loaded {total_links} links from {input_file}")
    
    # Create progress bar
    progress_bar = tqdm(total=total_links, desc="Checking links")
    
    try:
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(check_link, i, link) for i, link in enumerate(links)]
            
            # Process results as they complete
            for future in futures:
                try:
                    result = future.result()
                    process_result(result, progress_bar)
                    progress_bar.update(1)
                except Exception as e:
                    logger.error(f"Error processing result: {str(e)}")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected. Saving progress...")
        pass
    finally:
        # Final save
        save_results()
        progress_bar.close()
    
    # Log results
    logger.info(f"Found {len(inactive_links)} inactive links out of {total_links}")
    logger.info(f"Keeping {len(active_links)} active links")
    
    return len(active_links), len(inactive_links)

if __name__ == "__main__":
    try:
        active_count, inactive_count = clean_car_links()
        print(f"\nSummary:")
        print(f"Found {inactive_count} inactive links")
        print(f"Found {active_count} active links")
        print(f"Results saved to results/active_links.json and results/inactive_links.json")
        print(f"Original car_links.json file was not modified")
        print("Complete!")
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Results so far have been saved.")
        print(f"Processed {links_processed}/{total_links} links")
        print(f"Found {len(inactive_links)} inactive and {len(active_links)} active links")
        print("Partial results have been saved to the results directory.") 