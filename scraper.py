import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_text(text):
    if text:
        return text.strip().replace('\n', ' ')
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

    # SEARCH TERM PREPARATION
    search_term = None
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # 1. Go to the Year Archive
            target_url = f"{base_url}{dt_obj.year}"
            
            # 2. Create a loose search term: "Oct 25"
            # This avoids issues with commas, dots, or "Wednesday"
            # %b = Oct, %d = 25 (zero padded). We strip zero padding manually just in case
            month_str = dt_obj.strftime("%b")
            day_str = str(dt_obj.day) # "25" or "5" (no zero)
            search_term = f"{month_str} {day_str}" 
            
        except ValueError:
            data['error'] = "Invalid date format. Use YYYY-MM-DD"
            return data
            
    data['debug_url'] = target_url

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        target_row = None
        
        # LOGIC A: HISTORY SEARCH (Row Scanner)
        if date_str and search_term:
            # Look through all 'tr' (table rows) on the page
            rows = soup.find_all('tr')
            for row in rows:
                # cleanup row text to make matching easier
                row_txt = " ".join(row.text.split()) 
                
                # Check if "Oct 25" is inside the row text
                if search_term in row_txt:
                    target_row = row
                    break
            
            if not target_row:
                data['error'] = f"Date not found. Searched page for '{search_term}'"

        # LOGIC B: LATEST (First Row)
        else:
            # Find the first row that has numbers in it
            rows = soup.find_all('tr')
            for row in rows:
                if any(char.isdigit() for char in row.text):
                    target_row = row
                    break

        # EXTRACT NUMBERS
        if target_row:
            # Find all list items (li) or spans
            balls = target_row.find_all('li')
            if not balls:
                balls = target_row.find_all('span', class_=re.compile(r'ball|result'))
            
            for ball in balls:
                txt = clean_text(ball.text)
                if txt and txt.isdigit():
                    data['winning_numbers'].append(txt)
            
            # --- CRITICAL FIX: LIMIT TO 6 NUMBERS ---
            # Powerball is 5 white + 1 red. 
            # Aggregator sites often list "Double Play" numbers next to it.
            if len(data['winning_numbers']) > 6:
                data['winning_numbers'] = data['winning_numbers'][:6]
                
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return scrape_lottery_usa("texas", "powerball", date_str)
