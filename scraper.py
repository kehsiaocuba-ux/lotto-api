import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_text(text):
    if text:
        return text.strip().replace('\n', ' ')
    return None

def get_florida_data(date_str=None):
    data = {
        "state": "FL",
        "game": "Powerball",
        "winning_numbers": [],
        "debug_info": "v3_aggressive"
    }
    
    # 1. Determine URL
    if date_str:
        # If searching history, we use the search URL
        url = "https://www.flalottery.com/site/winning-numbers-search"
        # Note: Search usually requires POST data, but for now we test GET on main page
        # to ensure basic connectivity.
        url = "https://www.flalottery.com/powerball"
    else:
        url = "https://www.flalottery.com/powerball"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- STRATEGY 1: Look for 'gamePage-balls' (Common in FL) ---
        balls = soup.find_all('span', class_=re.compile(r'ball|number'))
        
        # --- STRATEGY 2: Look for specific blocks ---
        if not balls:
            game_header = soup.find('div', class_='gamePage-header')
            if game_header:
                balls = game_header.find_all('span')
        
        # Extract numbers
        for ball in balls:
            txt = clean_text(ball.text)
            # We only want balls that are 1 or 2 digits (e.g. "05", "10")
            # We filter out text like "Powerball" or "X2"
            if txt and txt.isdigit() and len(txt) <= 2:
                data['winning_numbers'].append(txt)

        # Remove duplicates while keeping order
        data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
        
        # Limit to first 6 numbers (5 white + 1 red usually)
        if len(data['winning_numbers']) > 6:
             data['winning_numbers'] = data['winning_numbers'][:6]

    except Exception as e:
        data['error'] = str(e)

    return data

def get_texas_data(date_str=None):
    data = {
        "state": "TX",
        "game": "Powerball",
        "winning_numbers": [],
        "debug_info": "v3_aggressive"
    }
    url = "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/index.html"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Texas uses a table structure often
        # Strategy: Find the "Current Winning Numbers" table
        
        # Look for any table cell containing numbers
        cells = soup.find_all('td')
        found_count = 0
        
        for cell in cells:
            txt = clean_text(cell.text)
            # Heuristic: Texas numbers often appear as just digits in a cell
            if txt and txt.isdigit():
                data['winning_numbers'].append(txt)
                found_count += 1
                
            # If we found enough numbers for one draw, stop (to avoid grabbing history)
            if found_count >= 6:
                break
                
    except Exception as e:
        data['error'] = str(e)
        
    return data
