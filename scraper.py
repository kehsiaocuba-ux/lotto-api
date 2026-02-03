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

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game):
    data = {
        "source": "lotteryusa.com",
        "winning_numbers": [],
        "debug_url": ""
    }
    # Latest numbers are usually best fetched from state-specific pages on Aggregators
    url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
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

            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

# --- SOURCE 2: LOTTERY.NET (HISTORY) ---
def scrape_history(state, game, date_obj):
    data = {
        "source": "lottery.net",
        "winning_numbers": [],
        "debug_url": ""
    }
    
    # CRITICAL FIX: Use National URL for Powerball
    # Powerball numbers are the same everywhere.
    if "powerball" in game.lower():
        url = f"https://www.lottery.net/powerball/numbers/{date_obj.year}"
    else:
        # Fallback for other games
        url = f"https://www.lottery.net/{game.lower()}/numbers/{date_obj.year}"
        
    data['debug_url'] = url
    
    # Create Search Variations
    # 1. "Oct 25"
    v1 = date_obj.strftime("%b %-d")
    v2 = date_obj.strftime("%b %d")
    # 2. "October 25" (Full Month)
    v3 = date_obj.strftime("%B %-d")
    v4 = date_obj.strftime("%B %d")
    
    search_terms = [v1, v2, v3, v4]
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        
        rows = soup.find_all('tr')
        for row in rows:
            row_txt = " ".join(row.text.split())
            
            # Check if any of our date variations exist in this row
            for term in search_terms:
                if term in row_txt:
                    target_row = row
                    break
            if target_row: break
        
        if target_row:
            # Found the date! Extract numbers.
            # Lottery.net usually puts numbers in <li> with class "ball"
            # But sometimes just in <td>. Let's be generic.
            
            # 1. Try specific balls first
            balls = target_row.find_all('li')
            if not balls:
                balls = target_row.find_all('span', class_='ball')
            
            # 2. Fallback to generic text extraction if no balls found
            if not balls:
                balls = target_row.find_all('td')

            for ball in balls:
                # Avoid the date column
                if any(x in ball.text for x in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']):
                    continue
                
                num = extract_number(ball.text)
                if num:
                    data['winning_numbers'].append(num)
            
            # Dedupe and Limit
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
        else:
            data['error'] = f"Date not found in archive. Searched for {search_terms}"
            
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
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # History Logic
            result = scrape_history(state, game, dt_obj)
            data.update(result)
        except ValueError:
            data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        # Latest Logic
        result = scrape_latest(state, game)
        data.update(result)
        
    return data

def get_florida_data(date_str=None):
    return get_lotto_data("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return get_lotto_data("texas", "powerball", date_str)
