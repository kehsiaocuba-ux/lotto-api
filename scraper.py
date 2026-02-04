import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Mimic a Real Browser exactly
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/'
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
    
    # STATE (Mapped to LotteryPost names)
    if "floridalotto" in g or g == "lotto": return ("Lotto", 6, False)
    if "jackpot" in g: return ("Jackpot Triple Play", 6, False)
    if "fantasy" in g: return ("Fantasy 5", 5, False)
    if "pick2" in g: return ("Pick 2", 2, False)
    if "pick3" in g: return ("Pick 3", 3, False)
    if "pick4" in g: return ("Pick 4", 4, False)
    if "pick5" in g: return ("Pick 5", 5, False)
    
    return (game_input, 6, False)

# --- RAW TEXT SCANNER (GAME MODE) ---
def scan_page_for_game(full_text, game_name, limit):
    """
    Finds 'Pick 3' in the text, then grabs the next numbers.
    """
    winning_numbers = []
    
    # 1. Find the game name index (Case Insensitive)
    idx = full_text.lower().find(game_name.lower())
    
    if idx == -1:
        # Fallback for "Florida Lotto" vs just "Lotto"
        if "lotto" in game_name.lower():
            idx = full_text.lower().find("lotto")
    
    if idx == -1:
        return [], f"Game Name '{game_name}' not found in page text."
    
    # 2. Look at the text IMMEDIATELY after the game name (400 chars)
    # This covers headers like "Pick 3 Evening: 1-2-3"
    snippet = full_text[idx:idx+400]
    
    # 3. Extract digits
    candidates = re.findall(r'\b\d{1,2}\b', snippet)
    
    for num in candidates:
        winning_numbers.append(num)
        
    # Heuristic: LotteryPost usually lists the numbers right after the name.
    if len(winning_numbers) >= limit:
        return winning_numbers[:limit], None
        
    return [], f"Game '{game_name}' found, but no numbers followed. Snippet: [{snippet[:50]}...]"

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    usa_slug = game_slug.replace("florida-", "").lower().replace(" ", "-")
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

# --- SOURCE 2: LOTTERY POST (HISTORY - ALL GAMES) ---
def scrape_history(state, game_name, date_obj, limit):
    data = {"source": "lotterypost.com", "winning_numbers": [], "debug_url": ""}
    
    abbr = get_state_abbr(state)
    date_url = date_obj.strftime("%Y/%m/%d")
    # URL: https://www.lotterypost.com/results/fl/2023/10/24
    url = f"https://www.lotterypost.com/results/{abbr}/{date_url}"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        # Security Check
        if "captcha" in response.text.lower() or "challenge" in response.text.lower():
             data['error'] = "Blocked by Cloudflare Captcha"
             return data
             
        # Convert to text
        soup = BeautifulSoup(response.content, 'html.parser')
        full_text = soup.get_text(" ")
        
        nums, err = scan_page_for_game(full_text, game_name, limit)
        if nums:
            data['winning_numbers'] = nums
        else:
            data['error'] = err
            
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
            # Unified History Source for everything
            result = scrape_history(state, clean_name, dt_obj, limit)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_name, limit)
        data.update(result)
    return data
