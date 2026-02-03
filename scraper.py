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
        "date_requested": date_str if date_str else "Latest"
    }
    
    # Base URL construction
    base_url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    target_url = base_url

    # FORMATTING THE DATE
    # We need to turn "2023-10-25" into "Oct 25, 2023" to match the website text
    formatted_date_search = None
    
    if date_str:
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # 1. Point to the Year Archive URL
            target_url = f"{base_url}{dt_obj.year}"
            # 2. Create the search string (e.g., "Oct 25, 2023")
            # %b = Abbreviated Month (Oct), %d = Day (25), %Y = Year (2023)
            formatted_date_search = dt_obj.strftime("%b %-d, %Y")
            
            # Windows/Mac difference: If %-d fails (removing zero padding), fallback to %d
            # But mostly, let's try a simpler matching logic in the loop below.
        except ValueError:
            data['error'] = "Invalid date format. Use YYYY-MM-DD"
            return data

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # FIND THE TABLE
        # Archives usually use a standard <table>
        tables = soup.find_all('table')
        
        target_row = None
        
        # LOGIC A: HISTORY SEARCH
        if date_str and formatted_date_search:
            # Loop through all rows in all tables to find the date
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    row_text = row.text
                    # Check if our date string (e.g. "Oct 25, 2023") is inside this row
                    # We accept "Oct 25" or "10/25" just to be safe
                    
                    # Create a few variations to search for
                    v1 = dt_obj.strftime("%b %d, %Y") # Oct 25, 2023
                    v2 = dt_obj.strftime("%B %d, %Y") # October 25, 2023
                    v3 = dt_obj.strftime("%m/%d/%Y")  # 10/25/2023
                    
                    if (v1 in row_text) or (v2 in row_text) or (v3 in row_text):
                        target_row = row
                        break
                if target_row: break
            
            if not target_row:
                data['error'] = f"Could not find entry for {date_str} (Searched for {formatted_date_search})"

        # LOGIC B: LATEST (No date)
        else:
            # Just grab the very first data row from the first table
            if tables:
                rows = tables[0].find_all('tr')
                # Usually row 0 is header, row 1 is latest data
                for row in rows:
                    # heuristic: check if it has numbers
                    if any(char.isdigit() for char in row.text):
                        target_row = row
                        break

        # EXTRACT NUMBERS FROM THE FOUND ROW
        if target_row:
            # The numbers are usually in a <ul> or just distinct items
            # Method 1: Look for <li> (Common in LotteryUSA)
            balls = target_row.find_all('li')
            
            # Method 2: If no <li>, look for spans with number class
            if not balls:
                balls = target_row.find_all('span', class_=re.compile(r'ball|result'))
            
            for ball in balls:
                txt = clean_text(ball.text)
                if txt and txt.isdigit():
                    data['winning_numbers'].append(txt)
            
            # Clean up: sometimes they list the Powerball twice (as number and as special)
            # We keep it simple.
            
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return scrape_lottery_usa("texas", "powerball", date_str)
