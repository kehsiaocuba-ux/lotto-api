import requests
import ssl
from bs4 import BeautifulSoup
import re
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util.ssl_ import create_urllib3_context

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- 1. LEGACY SSL ADAPTER (The Key Fix) ---
# This allows us to connect to the old Florida Lottery server
class LegacyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        # Create a custom SSL context
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        # LOWER SECURITY LEVEL to allow legacy ciphers (SECLEVEL=1)
        # This fixes the SSLV3 Handshake Failure
        try:
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        except Exception:
            # Fallback if system doesn't support SECLEVEL configuration
            ctx.set_ciphers('DEFAULT')
        
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

def get_game_config(game_input):
    g = game_input.lower().replace(" ", "").replace("-", "")
    # NATIONAL
    if "power" in g: return ("powerball", 6, True)
    if "mega" in g: return ("mega-millions", 6, True)
    if "cash" in g or "1000" in g: return ("cash4life", 6, True)
    
    # STATE (Mapped to Florida Legacy Codes)
    if "floridalotto" in g or g == "lotto": return ("l6", 6, False)
    if "jackpot" in g: return ("jtp", 6, False)
    if "fantasy" in g: return ("ff", 5, False)
    if "pick2" in g: return ("p2", 2, False)
    if "pick3" in g: return ("p3", 3, False)
    if "pick4" in g: return ("p4", 4, False)
    if "pick5" in g: return ("p5", 5, False)
    
    return (game_input, 6, False)

def extract_number(text):
    if not text: return None
    match = re.search(r'\d+', text)
    if match: return match.group(0)
    return None

# --- SOURCE 1: LOTTERY USA (LATEST) ---
def scrape_latest(state, game_slug, limit):
    usa_slug = game_slug
    # Map legacy codes back to USA slugs
    legacy_map = {"l6":"lotto", "jtp":"jackpot-triple-play", "ff":"fantasy-5", 
                  "p2":"pick-2", "p3":"pick-3", "p4":"pick-4", "p5":"pick-5"}
    if game_slug in legacy_map: usa_slug = legacy_map[game_slug]
    
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

# --- SOURCE 2: LOTTERY.NET (NATIONAL HISTORY) ---
# Reverted to V14 Logic which worked for Mega Millions
def scrape_national_history(game_slug, date_obj, limit):
    data = {"source": "lottery.net", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.lottery.net/{game_slug}/numbers/{date_obj.year}"
    data['debug_url'] = url
    
    search_terms = [
        date_obj.strftime("%b %-d"),       # Oct 25
        date_obj.strftime("%B %-d"),       # October 25
        date_obj.strftime("%A, %B %-d"),   # Tuesday, October 25
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
            candidates = re.findall(r'\b\d{1,2}\b', target_container.text)
            # Filter candidates: Month/Day often appear first.
            # But simpler heuristic: Grab all digits, check length.
            valid_nums = []
            for num in candidates:
                # Basic filter: don't add the year
                if len(num) == 4: continue
                valid_nums.append(num)
            
            # Remove duplicates? National games usually don't repeat numbers
            valid_nums = list(dict.fromkeys(valid_nums))
            
            # If we found too many, assume the last 'limit' are the winners
            if len(valid_nums) >= limit:
                 data['winning_numbers'] = valid_nums[-limit:]
        else:
            data['error'] = f"Date not found. Searched {search_terms}"
    except Exception as e:
        data['error'] = str(e)
    return data

# --- SOURCE 3: FLORIDA LEGACY TEXT (STATE HISTORY) ---
def scrape_florida_legacy(code, date_obj, limit):
    data = {"source": "flalottery.com (Text)", "winning_numbers": [], "debug_url": ""}
    url = f"https://www.flalottery.com/exptkt/{code}.html"
    data['debug_url'] = url
    
    # Format: 10/24/23 (Two digit year)
    search_date = date_obj.strftime("%m/%d/%y")
    
    try:
        # USE CUSTOM SSL ADAPTER
        session = requests.Session()
        session.mount('https://', LegacyAdapter())
        
        response = session.get(url, headers=HEADERS, timeout=15)
        lines = response.text.split('\n')
        
        target_line = None
        for line in lines:
            if search_date in line:
                target_line = line
                break # Takes the first match (usually Evening draw)
        
        if target_line:
            # Line format: 10/24/23  1-2-3-4
            # Remove the date
            clean_line = line.replace(search_date, "")
            # Extract numbers
            nums = re.findall(r'\d{1,2}', clean_line)
            if nums:
                data['winning_numbers'] = nums[:limit]
        else:
            data['error'] = f"Date {search_date} not found in file."
            
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
                result = scrape_florida_legacy(clean_slug, dt_obj, limit)
            else:
                data['error'] = "History only supported for Florida State Games currently"
            data.update(result)
        except ValueError: data['error'] = "Invalid format. Use YYYY-MM-DD"
    else:
        result = scrape_latest(state, clean_slug, limit)
        data.update(result)
    return data
