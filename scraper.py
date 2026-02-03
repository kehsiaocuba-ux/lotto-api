import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_number(text):
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
    
    # Ensure URL ends with slash to prevent redirects
    base_url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    target_url = base_url

    search_term = None
    
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            target_url = f"{base_url}{dt_obj.year}/"
            
            # Search for "Oct 25" (Month Abbr + Day)
            # This is the most common format on this site
            month_str = dt_obj.strftime("%b")
            day_str = str(dt_obj.day)
            search_term = f"{month_str} {day_str}" 
            
        except ValueError:
            data['error'] = "Invalid date format. Use YYYY-MM-DD"
            return data
            
    data['debug_url'] = target_url

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_container = None
        
        # LOGIC A: HISTORY (TEXT SEARCH)
        if date_str and search_term:
            # 1. Find the text node containing "Oct 25"
            # We use a regex to match "Oct 25" ignoring extra spaces
            text_node = soup.find(string=re.compile(re.escape(search_term)))
            
            if text_node:
                # 2. Walk up the tree to find the row/card container
                # Usually it's a <tr> or a <ul> or a <div>
                # We go up 2-3 levels to ensure we capture the numbers next to the date
                current = text_node.parent
                for _ in range(4): # Go up 4 levels max
                    if current.name in ['tr', 'div', 'ul', 'article']:
                        # Check if this container actually has numbers
                        if len(re.findall(r'\d{1,2}', current.text)) > 5:
                            target_container = current
                            break
                    if current.parent:
                        current = current.parent
            
            if not target_container:
                # DEBUG: If failed, show us what the page actually starts with
                # This helps us see if we are blocked (e.g. "Access Denied")
                page_text_sample = soup.get_text()[:200].replace('\n', ' ')
                data['error'] = f"Date '{search_term}' not found. Page Text Start: [{page_text_sample}]"

        # LOGIC B: LATEST
        else:
            # Find first container with lots of numbers
            rows = soup.find_all(['tr', 'ul'])
            for row in rows:
                if len(re.findall(r'\d', row.text)) > 4:
                    target_container = row
                    break

        # EXTRACT NUMBERS
        if target_container:
            # Look for ANY element that might hold a number
            elements = target_container.find_all(['li', 'span', 'td', 'div'])
            
            for el in elements:
                # Skip elements that look like dates or text
                txt = el.text.strip()
                if not txt: continue
                if ',' in txt or '/' in txt or ':' in txt: continue
                
                num = extract_number(txt)
                # Filter: Must be 1-2 digits (Lotto numbers aren't 100+)
                if num and len(num) <= 2: 
                    data['winning_numbers'].append(num)
            
            # Deduplicate
            data['winning_numbers'] = list(dict.fromkeys(data['winning_numbers']))
            
            # LIMIT TO 6
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return scrape_lottery_usa("texas", "powerball", date_str)
