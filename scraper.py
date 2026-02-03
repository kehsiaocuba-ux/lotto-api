import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- HELPERS ---
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
    # NATIONAL
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    # STATE
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
    # Adjust slug for LotteryUSA
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

# --- SOURCE 2: LOTTERY.NET (NATIONAL HISTORY) ---
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
        # Text search first
        for term in search_terms:
            el = soup.find(string=re.compile(re.escape(term), re.IGNORECASE))
            if el:
                # Walk up to find container
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
                if any(x in ball.text for x in [':', '/']) or len(ball.text) > 4: continue
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

# --- SOURCE 3: LOTTERY CORNER (STATE HISTORY) ---
def scrape_state_history(state, game_slug, date_obj, limit):
    data = {"source": "lotterycorner.com", "winning_numbers": [], "debug_url": ""}
    
    # Map state to abbr
    abbr = get_state_abbr(state)
    # URL: https://www.lotterycorner.com/fl/fantasy-5/winning-numbers/2023
    url = f"https://www.lotterycorner.com/{abbr}/{game_slug}/winning-numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Search: 10/21/2023 or 2023-10-21
    search_terms = [
        date_obj.strftime("%m/%d/%Y"),   # 10/21/2023
        date_obj.strftime("%Y-%m-%d"),   # 2023-10-21
        date_obj.strftime("%-m/%-d/%Y")  # 10/21/2023 (no zero pad)
    ]
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        rows = soup.find_all('tr')
        for row in rows:
            row_txt = " ".join(row.text.split())
            for term in search_terms:
                if term in row_txt:
                    target_row = row
                    break
            if target_row: break
            
        if target_row:
            # LotteryCorner usually puts numbers in <ul><li> or <span>
            # But sometimes just text in <td>
            elements = target_row.find_all(['li', 'span', 'td'])
            for el in elements:
                # Avoid the date column itself
                if '/' in el.text or ':' in el.text: continue
                
                num = extract_number(el.text)
                if num: data['winning_numbers'].append(num)
            
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
             data['error'] = f"Date not found. Searched {search_terms}"
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
