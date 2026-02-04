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

def get_game_config(game_input):
    g = game_input.lower().replace(" ", "").replace("-", "")
    # NATIONAL
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    
    # STATE (LotteryCorner Slugs)
    if "floridalotto" in g or g == "lotto": return ("florida-lotto", 6, False)
    if "jackpot" in g: return ("jackpot-triple-play", 6, False)
    if "fantasy" in g: return ("fantasy-5", 5, False)
    if "pick2" in g: return ("pick-2", 2, False)
    if "pick3" in g: return ("pick-3", 3, False)
    if "pick4" in g: return ("pick-4", 4, False)
    if "pick5" in g: return ("pick-5", 5, False)
    
    return (game_input.lower().replace(" ", "-"), 6, False)

# --- THE RAW TEXT SCANNER ---
def scan_text_for_numbers(full_text, date_variations, limit):
    winning_numbers = []
    found_date_used = ""
    
    idx = -1
    for date_str in date_variations:
        idx = full_text.lower().find(date_str.lower())
        if idx != -1:
            found_date_used = date_str
            break
    
    if idx == -1:
        return [], f"Date not found in text. Searched: {date_variations}"
    
    # Look at the text IMMEDIATELY after the date (300 chars)
    snippet = full_text[idx:idx+300]
    
    # Extract digits (1-2 chars long)
    # Filter out the year 2023 or 2024 to avoid false positives
    snippet_clean = snippet.replace("2023", "").replace("2024", "")
    
    candidates = re.findall(r'\b\d{1,2}\b', snippet_clean)
    
    for num in candidates:
        # Avoid day of month if it was picked up again
        winning_numbers.append(num)
        
    # Heuristic: LotteryCorner lists numbers immediately after date
    if len(winning_numbers) >= limit:
        return winning_numbers[:limit], None
        
    return [], f"Date '{found_date_used}' found, snippet: [{snippet[:50]}...]"

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    usa_slug = game_slug.replace("florida-", "")
    if usa_slug == "lotto": usa_slug = "lotto"
    
    data = {"source": "lotteryusa.com", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lotteryusa.com/{state.lower()}/{usa_slug}/"
    data['debug_url'] = url
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all(['tr', 'ul'])
        target_row = None
        for row in rows:
            if len(re.findall(r'\d', row.text)) >= limit:
                target_row = row
                break
        if target_row:
             candidates = re.findall(r'\b\d{1,2}\b', target_row.text)
             if len(candidates) >= limit:
                 data['winning_numbers'] = candidates[:limit]
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 2: LOTTERY CORNER (HISTORY - ALL GAMES) ---
def scrape_history(state, game_slug, date_obj, limit):
    data = {"source": "lotterycorner.com", "winning_numbers": [], "debug_url": ""}
    
    abbr = get_state_abbr(state)
    # URL: https://www.lotterycorner.com/fl/mega-millions/winning-numbers/2023
    url = f"https://www.lotterycorner.com/{abbr}/{game_slug}/winning-numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Search Terms for the Text Scanner
    # LotteryCorner format is usually: "Friday, October 24, 2023"
    search_terms = [
        date_obj.strftime("%m-%d-%Y"),   # 10-24-2023
        date_obj.strftime("%m/%d/%Y"),   # 10/24/2023
        date_obj.strftime("%b %-d"),      # Oct 24
        date_obj.strftime("%B %-d"),      # October 24
        date_obj.strftime("%Y-%m-%d"),    # 2023-10-24
    ]
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        # Convert entire HTML to clean text
        soup = BeautifulSoup(response.content, 'html.parser')
        full_text = soup.get_text(" ")
        
        nums, err = scan_text_for_numbers(full_text, search_terms, limit)
        if nums:
            data['winning_numbers'] = nums
        else:
            data['error'] = err
            
    except Exception as e:
        data['error'] = str(e)
    return data

# --- CONTROLLER ---
def get_lotto_data(state, game, date_str=None):
    clean_slug, limit, is_national = get_game_config(game)
    data = {"state": state.upper(), "game": clean_slug, "date_requested": date_str if date_str else "Latest", "limit_applied": limit}
    
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # Unified History Source for everything
            result = scrape_history(state, clean_slug, dt_obj, limit)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
    return data
