import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_number(text):
    if not text: return None
    match = re.search(r'\d+', text)
    if match:
        return match.group(0)
    return None

# --- SOURCE 1: LOTTERY USA (Best for LATEST) ---
def scrape_latest(state, game):
    data = {
        "source": "lotteryusa.com",
        "winning_numbers": [],
        "debug_url": ""
    }
    
    url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first row with digits
        rows = soup.find_all(['tr', 'ul'])
        target_row = None
        for row in rows:
            if len(re.findall(r'\d', row.text)) > 4:
                target_row = row
                break
                
        if target_row:
            elements = target_row.find_all(['li', 'span', 'td', 'div'])
            for el in elements:
                txt = el.text.strip()
                if not txt or ',' in txt or '/' in txt: continue
                
                num = extract_number(txt)
                if num and len(num) <= 2: 
                    data['winning_numbers'].append(num)

            # Dedupe and Limit
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

# --- SOURCE 2: LOTTERY.NET (Best for HISTORY) ---
def scrape_history(state, game, date_obj):
    data = {
        "source": "lottery.net",
        "winning_numbers": [],
        "debug_url": ""
    }
    
    # URL Pattern: https://www.lottery.net/florida-powerball/numbers/2023
    url = f"https://www.lottery.net/{state.lower()}-{game.lower()}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Search Terms: "Oct 25" and "10/25"
    month_str = date_obj.strftime("%b") # Oct
    day_str = str(date_obj.day)         # 25
    search_term = f"{month_str} {day_str}" 
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        
        # Lottery.net uses Tables. We scan rows.
        rows = soup.find_all('tr')
        for row in rows:
            # Normalize text to remove weird spaces
            row_txt = " ".join(row.text.split())
            
            if search_term in row_txt:
                target_row = row
                break
        
        if target_row:
            # Extract numbers from this row
            # They use <li> with class="ball" usually
            balls = target_row.find_all(['li', 'span'])
            
            for ball in balls:
                # Filter out Date column
                if "ball" not in str(ball): 
                     # If it's just a span without class, check if it's a number
                     if not ball.text.strip().isdigit():
                         continue

                num = extract_number(ball.text)
                if num:
                    data['winning_numbers'].append(num)
            
            # Dedupe and Limit
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
        else:
            data['error'] = f"Date '{search_term}' not found in archive."
            
    except Exception as e:
        data['error'] = str(e)

    return data

# --- CONTROLLER ---
def get_lotto_data(state, game, date_str=None):
    data = {
        "state": state.upper(),
        "game": game,
        "date_requested": date_str if date_str else "Latest",
    }
    
    if date_str:
        # User wants HISTORY
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            result = scrape_history(state, game, dt_obj)
            data.update(result)
        except ValueError:
            data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        # User wants LATEST
        result = scrape_latest(state, game)
        data.update(result)
        
    return data

def get_florida_data(date_str=None):
    return get_lotto_data("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return get_lotto_data("texas", "powerball", date_str)
