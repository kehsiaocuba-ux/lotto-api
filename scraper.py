import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_number(text):
    """
    Finds the first sequence of digits in a string.
    "PB 10" -> "10"
    "05" -> "05"
    """
    if not text: return None
    match = re.search(r'\d+', text)
    if match:
        return match.group(0)
    return None

def scrape_lottery_usa(state, game, date_str=None):
    data = {
        "state": state.upper(),
        "game": game,
        "source": "lotteryusa.com",
        "winning_numbers": [],
        "date_requested": date_str if date_str else "Latest",
        "debug_url": ""
    }
    
    base_url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    target_url = base_url

    # DATE SETUP
    search_variations = []
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # Point to Year Archive
            target_url = f"{base_url}{dt_obj.year}"
            
            # Create variations of the date to search for
            # 1. "Oct 25"
            search_variations.append(dt_obj.strftime("%b %-d"))
            search_variations.append(dt_obj.strftime("%b %d"))
            # 2. "October 25"
            search_variations.append(dt_obj.strftime("%B %-d"))
            # 3. "10/25"
            search_variations.append(dt_obj.strftime("%m/%d"))
            
        except ValueError:
            data['error'] = "Invalid date format. Use YYYY-MM-DD"
            return data
            
    data['debug_url'] = target_url

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        
        # LOGIC A: HISTORY SEARCH
        if date_str:
            rows = soup.find_all('tr')
            for row in rows:
                row_txt = " ".join(row.text.split()) 
                # Check if ANY of our variations match
                for term in search_variations:
                    if term in row_txt:
                        target_row = row
                        break
                if target_row: break
            
            if not target_row:
                # DEBUG: Capture the text of the first row found to see what's wrong
                first_row_sample = "No rows found"
                if rows:
                    first_row_sample = " ".join(rows[1].text.split()) if len(rows) > 1 else "Header only"
                data['error'] = f"Date not found. Searched for {search_variations}. Page sample: [{first_row_sample}]"

        # LOGIC B: LATEST
        else:
            rows = soup.find_all('tr')
            for row in rows:
                # Find first row with at least 3 digits in it (heuristic for numbers)
                if len(re.findall(r'\d', row.text)) > 3:
                    target_row = row
                    break

        # EXTRACT NUMBERS
        if target_row:
            # Gather all text from list items OR cells
            # This covers both <li> structure and <td> structure
            elements = target_row.find_all(['li', 'span', 'td'])
            
            for el in elements:
                # Don't grab the date column (usually has comma or /)
                if ',' in el.text or '/' in el.text:
                    continue
                    
                num = extract_number(el.text)
                if num and len(num) <= 2: # Lottos are usually 2 digits max
                    data['winning_numbers'].append(num)
            
            # Deduplicate (keep order)
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            
            # FORCE LIMIT TO 6 (5 White + 1 Red)
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return scrape_lottery_usa("texas", "powerball", date_str)
