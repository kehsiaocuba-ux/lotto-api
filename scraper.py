import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- MASTER CONFIGURATION ---
def get_game_config(game_input):
    g = game_input.lower().replace(" ", "").replace("-", "")
    
    # NATIONAL / MULTI-STATE
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    
    # STATE GAMES
    if "floridalotto" in g or g == "lotto": return ("lotto", 6, False)
    if "jackpot" in g: return ("jackpot-triple-play", 6, False)
    if "fantasy" in g: return ("fantasy-5", 5, False)
    if "pick2" in g: return ("pick-2", 2, False)
    if "pick3" in g: return ("pick-3", 3, False)
    if "pick4" in g: return ("pick-4", 4, False)
    if "pick5" in g: return ("pick-5", 5, False)
    
    return (game_input.lower().replace(" ", "-"), 6, False)

def extract_number(text):
    if not text: return None
    match = re.search(r'\d+', text)
    if match: return match.group(0)
    return None

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    data = {"source": "lotteryusa.com", "winning_numbers": [], "debug_url": ""}
    
    # Clean up slug
    site_slug = "lotto" if game_slug == "lotto" else game_slug
    url = f"https://www.lotteryusa.com/{state.lower()}/{site_slug}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first row/list with enough numbers
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

# --- SOURCE 2: LOTTERY.NET (HISTORY) ---
def scrape_history(state, game_slug, date_obj, limit, is_national):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    
    # URL GENERATION
    if is_national:
        url = f"https://www.lottery.net/{game_slug}/numbers/{date_obj.year}"
    else:
        prefix = f"{state.lower()}-"
        if game_slug.startswith(state.lower()): prefix = ""
        url = f"https://www.lottery.net/{prefix}{game_slug}/numbers/{date_obj.year}"
        
    data['debug_url'] = url
    
    # SEARCH TERMS (Expanded)
    search_terms = [
        date_obj.strftime("%b %-d"),      # Oct 25
        date_obj.strftime("%b %d"),       # Oct 25
        date_obj.strftime("%B %-d"),      # October 25
        date_obj.strftime("%m/%d/%Y"),    # 10/25/2023
        date_obj.strftime("%-m/%-d/%Y"),  # 10/25/2023
        date_obj.strftime("%Y-%m-%d")     # 2023-10-25
    ]
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # STRATEGY: TEXT NODE SEARCH
        # Find the text date, then look at its container/siblings
        target_container = None
        
        for term in search_terms:
            # Case insensitive search for the date string
            element = soup.find(string=re.compile(re.escape(term), re.IGNORECASE))
            if element:
                # We found the date text!
                # Now we look at the Parent ROW (tr) or CONTAINER (div)
                # Walk up 3 levels to find a container that holds numbers
                curr = element.parent
                for _ in range(3):
                    if curr.name in ['tr', 'div', 'article']:
                         # Check if this container has numbers in it
                         if len(re.findall(r'\d', curr.text)) >= limit:
                             target_container = curr
                             break
                    if curr.parent: curr = curr.parent
                if target_container: break
        
        if target_container:
            # Extract from container
            balls = target_container.find_all(['li', 'span', 'td', 'b'])
            for ball in balls:
                # Skip date text or day names
                if any(c in ball.text for c in ['/', ':', ',']) or len(ball.text) > 4: continue
                if any(m in ball.text for m in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']): continue
                
                num = extract_number(ball.text)
                if num: data['winning_numbers'].append(num)
            
            # Dedupe & Limit
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
            # DEBUG SAMPLE
            sample_text = soup.get_text()[:300].replace('\n', ' ')
            data['error'] = f"Date not found. Searched {search_terms}. Page Start: [{sample_text}]"
            
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
            result = scrape_history(state, clean_slug, dt_obj, limit, is_national)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
        
    return data
