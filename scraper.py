import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_state_abbr(state_name):
    states = {"florida": "fl", "texas": "tx", "new-york": "ny", "california": "ca"}
    return states.get(state_name.lower(), state_name[:2].lower())

def extract_number(text):
    if not text: return None
    match = re.search(r'\d+', text)
    if match: return match.group(0)
    return None

def get_game_config(game_input):
    g = game_input.lower().replace(" ", "").replace("-", "")
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    
    # State mapping (Text to find in LotteryPost headers)
    if "floridalotto" in g or g == "lotto": return ("Lotto", 6, False)
    if "jackpot" in g: return ("Jackpot Triple Play", 6, False)
    if "fantasy" in g: return ("Fantasy 5", 5, False)
    if "pick2" in g: return ("Pick 2", 2, False)
    if "pick3" in g: return ("Pick 3", 3, False)
    if "pick4" in g: return ("Pick 4", 4, False)
    if "pick5" in g: return ("Pick 5", 5, False)
    
    return (game_input, 6, False)

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    usa_slug = game_slug.lower().replace(" ", "-")
    if usa_slug == "lotto": usa_slug = "lotto" # FL Lotto special case
    
    data = {"source": "lotteryusa.com", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lotteryusa.com/{state.lower()}/{usa_slug}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        threshold = limit if limit < 4 else 4
        rows = soup.find_all(['tr', 'ul'])
        target_row = None
        for row in rows:
            if len(re.findall(r'\d', row.text)) >= threshold:
                target_row = row
                break
        if target_row:
            elements = target_row.find_all(['li', 'span', 'td', 'div'])
            for el in elements:
                txt = el.text.strip()
                if not txt or ',' in txt or '/' in txt: continue
                if "fire" in txt.lower() or "double" in txt.lower(): continue
                num = extract_number(txt)
                if num and len(num) <= 2: data['winning_numbers'].append(num)
            
            if "pick" not in usa_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 2: NATIONAL HISTORY (LOTTERY.NET - FUZZY MATCH) ---
def scrape_national_history(game_slug, date_obj, limit):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lottery.net/{game_slug.lower().replace(' ', '-')}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Fuzzy Search terms: Month and Day separately
    month_name = date_obj.strftime("%B") # October
    month_abbr = date_obj.strftime("%b") # Oct
    day_num = str(date_obj.day)          # 24
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        rows = soup.find_all('tr')
        for row in rows:
            txt = row.text
            # Check if Month AND Day appear in the row text
            if (month_name in txt or month_abbr in txt) and (day_num in txt):
                target_row = row
                break
        
        if target_row:
            balls = target_row.find_all(['li', 'span', 'td'])
            for ball in balls:
                if any(x in ball.text for x in [':', '/', ',']) or len(ball.text) > 4: continue
                num = extract_number(ball.text)
                if num: data['winning_numbers'].append(num)
            
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
            data['error'] = f"Date not found (Fuzzy match: {month_abbr} + {day_num})"
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 3: STATE HISTORY (LOTTERY POST - HEADER SCAN) ---
def scrape_lotterypost_daily(state, game_name, date_obj, limit):
    data = {"source": "lotterypost.com", "winning_numbers": [], "debug_url": ""}
    abbr = get_state_abbr(state)
    date_url_part = date_obj.strftime("%Y/%m/%d")
    url = f"https://www.lotterypost.com/results/{abbr}/{date_url_part}"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Find ALL Result Containers (Grid Cells)
        # LotteryPost uses 'results-grid' usually
        grids = soup.find_all('div', class_=re.compile(r'results-grid|result'))
        
        target_block = None
        
        # If grids found, iterate them to find the game name header
        if grids:
            for grid in grids:
                # Does this grid contain our game name?
                # Case insensitive check
                if game_name.lower() in grid.text.lower():
                    # Check if it has numbers
                    if len(re.findall(r'\d', grid.text)) >= limit:
                        target_block = grid
                        break
        
        # Fallback: Search generic headers h2/h3/h4
        if not target_block:
            headers = soup.find_all(['h2', 'h3', 'h4', 'a'])
            for h in headers:
                if game_name.lower() in h.text.lower():
                    # Look at next sibling or parent for numbers
                    container = h.parent
                    if len(re.findall(r'\d', container.text)) >= limit:
                        target_block = container
                        break
        
        if target_block:
            elements = target_block.find_all(['span', 'time', 'div'])
            nums = []
            for el in elements:
                if ':' in el.text or 'M' in el.text: continue # Skip time
                if "pick" in el.text.lower(): continue # Skip title
                
                num = extract_number(el.text)
                if num: nums.append(num)
                
            if nums:
                data['winning_numbers'] = nums
                if "Pick" not in game_name:
                    data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
                if len(data['winning_numbers']) > limit:
                    data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
             data['error'] = f"Game '{game_name}' not found on daily page."
             
    except Exception as e:
        data['error'] = str(e)
    return data

# --- CONTROLLER ---
def get_lotto_data(state, game, date_str=None):
    clean_name, limit, is_national = get_game_config(game)
    data = {"state": state.upper(), "game": clean_name, "date_requested": date_str if date_str else "Latest", "limit_applied": limit}
    
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if is_national:
                result = scrape_national_history(clean_name, dt_obj, limit)
            else:
                result = scrape_lotterypost_daily(state, clean_name, dt_obj, limit)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_name, limit)
        data.update(result)
    return data
