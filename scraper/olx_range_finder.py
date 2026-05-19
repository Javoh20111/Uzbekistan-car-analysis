"""
Price Range Finder Module

This module determines optimal price ranges for scraping car advertisements
from OLX.uz. It uses an adaptive algorithm to create price ranges that stay
under the platform's 1000 results per query limit.

The module works by:
- Starting with initial price ranges
- Checking result counts for each range
- Narrowing ranges that exceed 1000 results
- Expanding ranges that are well below the limit
- Optimizing to maximize coverage while staying under limits

Features:
- Adaptive binary search algorithm for optimal range sizing
- Automatic detection of 1000+ result limits
- Skips ranges with too few results (< 5)
- Saves ranges incrementally after each determination
- Handles errors gracefully with conservative fallbacks

The determined price ranges are saved to 'price_ranges.json' which can
then be used by link_extractor.py to extract car advertisement links.

Usage:
    python range_finder.py

Output:
    price_ranges.json: JSON file containing optimized price ranges
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import datetime
import re


base_url = 'https://www.olx.uz/transport/legkovye-avtomobili/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

def check_result_count(min_price, max_price):
    """Check how many results are in a price range without scraping"""
    url = f"{base_url}?currency=UYE&search%5Bfilter_float_price%3Afrom%5D={min_price}&search%5Bfilter_float_price%3Ato%5D={max_price}&search%5Border%5D=filter_float_price%3Adesc"
    
    try:
        print(f"Checking result count for range {min_price}-{max_price}...")
        response = requests.get(url, headers=headers, timeout=10)
        
        # Raises an HTTPError if the response status code indicates an error (4xx or 5xx)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        total_count_element = soup.find('span', attrs={'data-testid': 'total-count'})
        
        if total_count_element:
            count_text = total_count_element.text.strip()
            print(f"Found count text: {count_text}")
            
            # Check if it shows exactly 1000 or "1 000" which means it's over the limit
            if "1" in count_text and ("000" in count_text or "nbsp" in str(total_count_element)):
                print("Range has 1000+ results - need to narrow")
                return 1000
            
            # Parse the count text which might contain &nbsp; or spaces
            # Remove all non-digit characters and convert to int
            count_text = re.sub(r'\D', '', count_text)
            if count_text:
                count = int(count_text)
                print(f"Range has {count} results")
                return count
            
        print("Could not find result count")
        return None
    
    except Exception as e:
        print(f"Error checking result count: {e}")
        return None


def adaptive_price_ranges():
    """Adaptively determine price ranges to stay under 1000 results per range"""
    price_ranges = []
    current_min = 1000  # Starting price
    max_price = 150000  # Maximum price to consider
    
    while current_min < max_price:
        # Start with a reasonable increment 
        current_max = current_min + 200
        
        # If we're close to the end, just use the max price
        if current_max >= max_price:
            price_ranges.append((current_min, max_price))
            break
        
        count = check_result_count(current_min, current_max)
        
        if count is None:
            # If we couldn't get a count, use a conservative increment
            price_ranges.append((current_min, current_max))
            current_min = current_max + 1
            continue
        
        # Binary search to find the right upper bound
        if count >= 1000:
            # Too many results, need to narrow the range
            # Start with a smaller initial decrement (30) to avoid ranges with very few results
            current_max = current_min + 170  # Reduce by 30 from initial 200
            count = check_result_count(current_min, current_max)
            
            # If still over 1000, use a more gradual narrowing approach
            if count >= 1000:
                while count >= 1000 and current_max > current_min + 30:
                    # Reduce by 10 each time for finer control
                    current_max -= 10
                    count = check_result_count(current_min, current_max)
                    
                    if count is None:
                        # If error, be conservative
                        current_max = current_min + 50
                        break
            
            # If we've narrowed too much (very few results), expand a bit
            if count is not None and count < 100 and current_max < current_min + 150:
                print(f"Range too narrow with only {count} results, trying to expand slightly")
                # Try to get at least 100 results if possible
                test_max = current_max + 20
                test_count = check_result_count(current_min, test_max)
                if test_count is not None and test_count < 1000:
                    current_max = test_max
                    count = test_count
        else:
            # We can try to expand the range to utilize more of the 1000 limit
            original_max = current_max
            increment = 100  # Original increment for expansion
            
            while count < 950 and current_max < max_price:
                new_max = min(current_max + increment, max_price)
                new_count = check_result_count(current_min, new_max)
                
                if new_count is None or new_count >= 1000:
                    # If error or we went over 1000, revert to previous max
                    break
                
                current_max = new_max
                count = new_count
                
                # If we're getting close to 1000, reduce the increment
                if count > 800:
                    increment = max(10, increment // 2)
        
        # Only add ranges with meaningful numbers of results
        if count is not None and count < 5:
            print(f"Range {current_min}-{current_max} has too few results ({count}), skipping")
            current_min = current_max + 1
            continue
            
        # Add the optimized range
        price_ranges.append((current_min, current_max))
        print(f"Added price range: {current_min} - {current_max} with ~{count} results")
        
        # Save ranges to file after each new range is determined
        save_ranges_to_file(price_ranges)
        
        # Set next min price
        current_min = current_max + 1
        
        # Add a delay between range checks
        time.sleep(2)
    
    return price_ranges


def save_ranges_to_file(ranges):
    """Save the current set of price ranges to a file"""
    ranges_json_filename = os.path.join(os.path.dirname(__file__), 'data', 'olx_price_ranges.json')
    os.makedirs(os.path.dirname(ranges_json_filename), exist_ok=True)
    ranges_json_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_ranges": len(ranges),
        "price_ranges": ranges
    }
    
    with open(ranges_json_filename, 'w', encoding='utf-8') as ranges_file:
        json.dump(ranges_json_data, ranges_file, indent=2)
    
    print(f"Updated {ranges_json_filename} with {len(ranges)} price ranges")


if __name__ == "__main__":
    # Generate adaptive price ranges
    print("Generating adaptive price ranges to optimize data collection...")
    price_ranges = adaptive_price_ranges()

    print("\nDetermined optimal price ranges:")
    for i, (min_price, max_price) in enumerate(price_ranges):
        print(f"{i+1}. {min_price} - {max_price}")

    print(f"\nPrice ranges are saved in scraper/data/olx_price_ranges.json")
    print(f"\nTo extract links using these ranges, run:")
    print(f"python scraper/olx_link_extractor.py") 