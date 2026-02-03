import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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
    
    # State Games
    if "floridalotto" in g or g == "lotto": return ("florida-lotto", 6, False)
    if "jackpot" in g: return ("jackpot-triple-play", 6, False)
    if "fantasy" in g: return ("fantasy-5", 5, False)
    if "pick2" in g: return ("pick-2", 2, False)
    if "pick3" in g: return ("pick-3", 3, False)
    if "pick4" in g: return ("pick-4", 4, False)
    if "pick5" in g: return ("pick-5", 5, False)
    
    return (game_input.lower().replace(" ", "-"), 6, False)

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
    
    search_terms = [
        date_obj.strftime("%A, %B %-d, %Y"), # Tuesday, October 24, 2023
        date_obj.strftime("%b %-d"),
        date_obj.strftime("%B %-d")
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

# --- SOURCE 3: FLORIDA LEGACY FILES (NUCLEAR OPTION) ---
def scrape_florida_legacy(game_slug, date_obj, limit):
    data = {"source": "flalottery.com (Legacy Text)", "winning_numbers": [], "debug_url": ""}
    
    # Map game slug to Florida Legacy Code
    legacy_map = {
        "pick-3": "p3",
        "pick-4": "p4",
        "pick-5": "p5",
        "fantasy-5": "ff",
        "florida-lotto": "l6",
        "jackpot-triple-play": "jtp", # Might need verification
        "pick-2": "p2"
    }
    
    code = legacy_map.get(game_slug)
    if not code:
        data['error'] = "Game not supported in Legacy Mode"
        return data
        
    url = f"https://www.flalottery.com/exptkt/{code}.html"
    data['debug_url'] = url
    
    # Florida text files usually use format: 10/21/23
    search_date = date_obj.strftime("%m/%d/%y") # 10/24/23
    
    try:
        # These are text files, not HTML, but we use requests all the same
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        # Split by lines
        lines = response.text.split('\n')
        
        target_line = None
        for line in lines:
            if search_date in line:
                target_line = line
                # Pick games have Midday (M) and Evening (E). 
                # We usually want Evening (latest), which appears second usually,
                # but let's just grab the first match for now to ensure data.
                break
        
        if target_line:
            # Format is usually: 10/24/23  1-2-3
            # Or: 10/24/23  12-34-56-78
            # Extract all numbers that are NOT part of the date
            parts = target_line.split()
            nums_found = []
            
            for part in parts:
                if '/' in part: continue # Skip date
                # Split by dashes if they exist (1-2-3)
                if '-' in part:
                    sub_parts = part.split('-')
                    for sp in sub_parts:
                        n = extract_number(sp)
                        if n: nums_found.append(n)
                else:
                    n = extract_number(part)
                    if n: nums_found.append(n)
            
            data['winning_numbers'] = nums_found
            if "pick" not in game_slug:
                 data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                 data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
             data['error'] = f"Date {search_date} not found in Legacy File"
             
    except Exception as e:
        data['error'] = f"Legacy Error: {str(e)}"
        
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
            elif state.lower() == "florida":
                # Use Nuclear Option for Florida
                result = scrape_florida_legacy(clean_slug, dt_obj, limit)
            else:
                # Fallback for Texas state games (future expansion)
                data['error'] = "History not supported for this state yet"
                return data
                
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
    return data
