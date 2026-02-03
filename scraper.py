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
    if "floridalotto" in g or g == "lotto": return ("florida-lotto", 6, False)
    if "jackpot" in g: return ("jackpot-triple-play", 6, False)
    if "fantasy" in g: return ("fantasy-5", 5, False)
    if "pick2" in g: return ("pick-2", 2, False)
    if "pick3" in g: return ("pick-3", 3, False)
    if "pick4" in g: return ("pick-4", 4, False)
    if "pick5" in g: return ("pick-5", 5, False)
    return (game_input.lower().replace(" ", "-"), 6, False)

# --- GENERIC NUMBER FINDER ---
def find_numbers_near_date(soup, date_obj, limit):
    """
    Searches for the date in ANY format, finds the container, and extracts numbers.
    """
    # Generate ALL possible date formats
    search_terms = [
        date_obj.strftime("%b %-d"),       # Oct 25
        date_obj.strftime("%B %-d"),       # October 25
        date_obj.strftime("%m/%d/%Y"),     # 10/25/2023
        date_obj.strftime("%a, %b %-d"),   # Wed, Oct 25
        date_obj.strftime("%A, %B %-d"),   # Wednesday, October 25
        date_obj.strftime("%Y-%m-%d")      # 2023-10-25
    ]
    
    target_container = None
    matched_term = ""
    
    # 1. Text Search
    for term in search_terms:
        # Case insensitive search
        el = soup.find(string=re.compile(re.escape(term), re.IGNORECASE))
        if el:
            matched_term = term
            # Walk up 3 levels (Text -> Span -> Td -> Tr)
            curr = el.parent
            for _ in range(4):
                if curr.name in ['tr', 'div', 'li']: 
                    # Check if this container has numbers
                    if len(re.findall(r'\d', curr.text)) >= limit:
                        target_container = curr
                        break
                if curr.parent: curr = curr.parent
            if target_container: break
            
    if not target_container:
        return [], f"Date not found. Searched {search_terms}"
        
    # 2. Extract Numbers from Container
    winning_numbers = []
    # Find anything that looks like a ball/cell
    elements = target_container.find_all(['li', 'span', 'td', 'div', 'b'])
    
    for el in elements:
        txt = el.text.strip()
        # Filter out junk
        if not txt: continue
        if any(c in txt for c in [':', '/', ',']): continue # Date parts
        if len(txt) > 4: continue # Long text
        if any(m in txt for m in ['Jan','Feb','Oct','Nov']): continue # Months
        
        num = extract_number(txt)
        if num: winning_numbers.append(num)
        
    return winning_numbers, None

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    site_slug = "lotto" if game_slug == "florida-lotto" else game_slug
    data = {"source": "lotteryusa.com", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lotteryusa.com/{state.lower()}/{site_slug}/"
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
            
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 2: NATIONAL HISTORY (LOTTERY.NET) ---
def scrape_national_history(game_slug, date_obj, limit):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lottery.net/{game_slug}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        nums, err = find_numbers_near_date(soup, date_obj, limit)
        
        if err: 
            data['error'] = err
        else:
            data['winning_numbers'] = nums
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                 data['winning_numbers'] = data['winning_numbers'][:limit]
                 
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 3: STATE HISTORY (LOTTERY CORNER) ---
def scrape_state_history(state, game_slug, date_obj, limit):
    data = {"source": "lotterycorner.com", "winning_numbers": [], "debug_url": ""}
    abbr = get_state_abbr(state)
    url = f"https://www.lotterycorner.com/{abbr}/{game_slug}/winning-numbers/{date_obj.year}"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        nums, err = find_numbers_near_date(soup, date_obj, limit)
        
        if err:
            # Fallback: Sometimes LotteryCorner URL is different for multi-word games
            # e.g. "pick-3" might be "pick-3" but "florida-lotto" might be "lotto"
            # If failed, we return error, but user can tweak URL in future.
            data['error'] = err
        else:
            data['winning_numbers'] = nums
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                 data['winning_numbers'] = data['winning_numbers'][:limit]
                 
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
            if is_national:
                result = scrape_national_history(clean_slug, dt_obj, limit)
            else:
                result = scrape_state_history(state, clean_slug, dt_obj, limit)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
    return data
