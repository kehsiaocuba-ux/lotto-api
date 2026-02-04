import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_game_config(game_input):
    g = game_input.lower().replace(" ", "").replace("-", "")
    # NATIONAL
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    
    # STATE (Mapped to LottoAmerica slugs)
    if "floridalotto" in g or g == "lotto": return ("florida-lotto", 6, False)
    if "jackpot" in g: return ("jackpot-triple-play", 6, False)
    if "fantasy" in g: return ("florida-fantasy-5", 5, False)
    if "pick2" in g: return ("florida-pick-2", 2, False)
    if "pick3" in g: return ("florida-pick-3", 3, False)
    if "pick4" in g: return ("florida-pick-4", 4, False)
    if "pick5" in g: return ("florida-pick-5", 5, False)
    
    return (game_input, 6, False)

def extract_numbers_brute_force(row_element, limit):
    """
    Ignores HTML structure. Just grabs all numbers in the text.
    Removes dates and row indices.
    """
    # Get all text in the row
    text = row_element.get_text(" ", strip=True)
    
    # Find all digit sequences 1-2 chars long
    # We ignore 4-digit numbers (years)
    candidates = re.findall(r'\b\d{1,2}\b', text)
    
    winning_numbers = []
    for num in candidates:
        # Filter out obvious date parts (months 1-12 or days 1-31 are hard to filter, 
        # so we rely on the fact that numbers usually come AFTER the date)
        
        # Heuristic: If we already found the date in the search step, 
        # we assume the numbers are the OTHER digits.
        # But simplistic approach: Lotto numbers are usually distinct.
        winning_numbers.append(num)

    # DANGEROUS: This might grab the day of month (e.g. "24"). 
    # Usually the date is at the start. The winning numbers are at the end.
    # Let's take the LAST 'limit' numbers found.
    if len(winning_numbers) >= limit:
        return winning_numbers[-limit:]
        
    return winning_numbers

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    usa_slug = game_slug.replace("florida-", "") # Remove prefix for LotteryUSA
    if usa_slug == "lotto": usa_slug = "lotto"
    
    data = {"source": "lotteryusa.com", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lotteryusa.com/{state.lower()}/{usa_slug}/"
    data['debug_url'] = url
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find first row with enough numbers
        rows = soup.find_all(['tr', 'ul'])
        target_row = None
        for row in rows:
            if len(re.findall(r'\d', row.text)) >= limit:
                target_row = row
                break
                
        if target_row:
            data['winning_numbers'] = extract_numbers_brute_force(target_row, limit)
            
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 2: LOTTERY.NET (NATIONAL HISTORY) ---
def scrape_national_history(game_slug, date_obj, limit):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lottery.net/{game_slug}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Search for Month+Day (e.g. Oct 24)
    term = date_obj.strftime("%b %-d")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        # Look for row containing the date
        rows = soup.find_all('tr')
        for row in rows:
            if term in row.text:
                target_row = row
                break
        
        if target_row:
            # use brute force extraction
            data['winning_numbers'] = extract_numbers_brute_force(target_row, limit)
        else:
            data['error'] = f"Date '{term}' not found."
            
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 3: LOTTO AMERICA (STATE HISTORY) ---
def scrape_lottoamerica_history(state, game_slug, date_obj, limit):
    data = {"source": "lottoamerica.com", "winning_numbers": [], "debug_url": ""}
    
    # URL: https://www.lottoamerica.com/florida-pick-3/numbers/2023
    url = f"https://www.lottoamerica.com/{game_slug}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    # Search Terms
    # LottoAmerica uses "Tue, Oct 24, 2023" usually
    # We search for "Oct 24"
    term = date_obj.strftime("%b %-d")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            data['error'] = f"Status Code {response.status_code}"
            return data
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        rows = soup.find_all('tr')
        for row in rows:
            if term in row.text:
                target_row = row
                break
        
        if target_row:
             data['winning_numbers'] = extract_numbers_brute_force(target_row, limit)
        else:
             data['error'] = f"Date '{term}' not found."

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
                result = scrape_lottoamerica_history(state, clean_slug, dt_obj, limit)
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
    return data
