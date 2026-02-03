import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- MASTER CONFIGURATION ---
# This maps your URL input to the correct website logic
def get_game_config(game_input):
    """
    Returns: (clean_slug, number_limit, is_national_history)
    """
    g = game_input.lower().replace(" ", "").replace("-", "")
    
    # POWERBALL
    if "power" in g: 
        return ("powerball", 6, True)
    
    # MEGA MILLIONS
    if "mega" in g: 
        return ("mega-millions", 6, True)
    
    # CASH 4 LIFE (1000 a day for life)
    if "cash" in g or "1000" in g: 
        return ("cash4life", 6, True)
    
    # FLORIDA LOTTO
    if "floridalotto" in g or g == "lotto": 
        return ("lotto", 6, False)
        
    # JACKPOT TRIPLE PLAY
    if "jackpot" in g or "triple" in g:
        return ("jackpot-triple-play", 6, False)
    
    # FANTASY 5
    if "fantasy" in g:
        return ("fantasy-5", 5, False)

    # PICK GAMES
    # Note: LotteryUSA uses 'pick-3', Lottery.net uses 'florida-pick-3'
    if "pick2" in g: return ("pick-2", 2, False)
    if "pick3" in g: return ("pick-3", 3, False)
    if "pick4" in g: return ("pick-4", 4, False)
    if "pick5" in g: return ("pick-5", 5, False)
    
    # Default fallback
    return (game_input.lower().replace(" ", "-"), 6, False)

def extract_number(text):
    if not text: return None
    match = re.search(r'\d+', text)
    if match:
        return match.group(0)
    return None

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    data = {
        "source": "lotteryusa.com",
        "winning_numbers": [],
        "debug_url": ""
    }
    
    # Clean up slug for LotteryUSA (they use 'lotto', not 'florida-lotto' usually inside the florida folder)
    site_slug = game_slug
    if game_slug == "lotto": site_slug = "lotto" 
    
    url = f"https://www.lotteryusa.com/{state.lower()}/{site_slug}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Heuristic: Find first row/list with enough numbers
        # Use a lower threshold for Pick 2/3
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
                # Skip "Fireball" or "Double Play" text
                if "fire" in txt.lower() or "double" in txt.lower(): continue
                
                num = extract_number(txt)
                if num and len(num) <= 2: 
                    data['winning_numbers'].append(num)

            # Dedupe (Only if not a Pick game, because Pick games can have repeat numbers like 1-1-1)
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            
            # Strict Limit
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

# --- SOURCE 2: LOTTERY.NET (HISTORY) ---
def scrape_history(state, game_slug, date_obj, limit, is_national):
    data = {
        "source": "lottery.net",
        "winning_numbers": [],
        "debug_url": ""
    }
    
    # URL GENERATION
    if is_national:
        # e.g. https://www.lottery.net/cash4life/numbers/2023
        url = f"https://www.lottery.net/{game_slug}/numbers/{date_obj.year}"
    else:
        # e.g. https://www.lottery.net/florida-pick-3/numbers/2023
        # Lottery.net requires state prefix for state games
        # Special case: Florida Lotto -> florida-lotto
        prefix = f"{state.lower()}-"
        if game_slug.startswith(state.lower()): prefix = "" # Avoid florida-florida-lotto
        
        full_slug = f"{prefix}{game_slug}"
        url = f"https://www.lottery.net/{full_slug}/numbers/{date_obj.year}"
        
    data['debug_url'] = url
    
    # Search Terms
    search_terms = [
        date_obj.strftime("%b %-d"),
        date_obj.strftime("%b %d"),
        date_obj.strftime("%B %-d"),
        date_obj.strftime("%B %d"),
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
            balls = target_row.find_all(['li', 'span', 'td'])
            for ball in balls:
                if any(x in ball.text for x in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']): continue
                if "sum" in ball.text.lower(): continue # Skip "Sum It Up" numbers
                
                num = extract_number(ball.text)
                if num:
                    data['winning_numbers'].append(num)
            
            # Dedupe (Non-Pick games only)
            if "pick" not in game_slug:
                data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
                
            if len(data['winning_numbers']) > limit:
                data['winning_numbers'] = data['winning_numbers'][:limit]
        else:
            data['error'] = f"Date not found. Searched for {search_terms}"
            
    except Exception as e:
        data['error'] = str(e)

    return data

# --- CONTROLLER ---
def get_lotto_data(state, game, date_str=None):
    # 1. Get Configuration for this game
    clean_slug, limit, is_national = get_game_config(game)
    
    data = {
        "state": state.upper(),
        "game": clean_slug,
        "date_requested": date_str if date_str else "Latest",
        "limit_applied": limit
    }
    
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            result = scrape_history(state, clean_slug, dt_obj, limit, is_national)
            data.update(result)
        except ValueError:
            data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
        
    return data
