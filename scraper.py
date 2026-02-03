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
    
    # State mapping for LotteryPost
    # Key = Input Slug, Value = Text to search on LotteryPost
    if "floridalotto" in g or g == "lotto": return ("Florida Lotto", 6, False)
    if "jackpot" in g: return ("Jackpot Triple Play", 6, False)
    if "fantasy" in g: return ("Fantasy 5", 5, False)
    if "pick2" in g: return ("Pick 2", 2, False)
    if "pick3" in g: return ("Pick 3", 3, False)
    if "pick4" in g: return ("Pick 4", 4, False)
    if "pick5" in g: return ("Pick 5", 5, False)
    
    return (game_input, 6, False)

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    # Map back to LotteryUSA slug format
    usa_slug = game_slug.lower().replace(" ", "-")
    if usa_slug == "florida-lotto": usa_slug = "lotto"
    
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

# --- SOURCE 2: NATIONAL HISTORY (LOTTERY.NET) ---
def scrape_national_history(game_slug, date_obj, limit):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lottery.net/{game_slug.lower().replace(' ', '-')}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    search_terms = [
        date_obj.strftime("%A, %B %-d, %Y"), # Tuesday, October 24, 2023
        date_obj.strftime("%a, %b %-d, %Y"), # Tue, Oct 24, 2023
        date_obj.strftime("%b %-d"),
    ]
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_container = None
        for term in search_terms:
            el = soup.find(string=re.compile(re.escape(term), re.IGNORECASE))
            if el:
                curr = el.parent
                for _ in range(4):
                    if curr.name == 'tr': 
                        target_container = curr
                        break
                    if curr.parent: curr = curr.parent
                if target_container: break
        
        if target_container:
            balls = target_container.find_all(['li', 'span', 'td'])
            for ball in balls:
                if any(x in ball.text for x in [':', '/', ',']) or len(ball.text) > 4: continue
                num = extract_number(ball.text)
                if num: data['winning_numbers'].append(num)
            
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
            data['error'] = f"Date not found. Searched {search_terms}"
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 3: STATE HISTORY (LOTTERY POST DAILY PAGE) ---
def scrape_lotterypost_daily(state, game_name, date_obj, limit):
    data = {"source": "lotterypost.com", "winning_numbers": [], "debug_url": ""}
    abbr = get_state_abbr(state)
    
    # URL Format: https://www.lotterypost.com/results/fl/2023/10/21
    date_url_part = date_obj.strftime("%Y/%m/%d")
    url = f"https://www.lotterypost.com/results/{abbr}/{date_url_part}"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # LotteryPost lists games in blocks. We search for the Game Name (e.g. "Pick 5")
        # Then grab the numbers in that same block.
        
        # Find all game titles
        headers = soup.find_all(['h2', 'a'], string=re.compile(re.escape(game_name), re.IGNORECASE))
        
        target_block = None
        
        for header in headers:
            # We want to match "Pick 5 Evening" or just "Pick 5"
            # We prefer "Evening" if available, but take first match.
            # Walk up to the row container
            curr = header.parent
            for _ in range(3):
                if curr.name == 'div' and 'results-grid' in str(curr.get('class', [])):
                   pass # Keep going up? LotteryPost structure varies
                if curr.name == 'div' or curr.name == 'tr':
                    # Check if this container has numbers
                    if len(re.findall(r'\d', curr.text)) >= limit:
                        target_block = curr
                        break
                if curr.parent: curr = curr.parent
            if target_block: break
            
        if target_block:
            # Extract numbers
            # They use <span class="sprite-ball"> or just text
            elements = target_block.find_all(['span', 'time'])
            
            nums = []
            for el in elements:
                # Skip times (e.g. 9:00 PM)
                if ':' in el.text or 'M' in el.text: continue
                
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
