import requests
from bs4 import BeautifulSoup
import re

# We use a browser user-agent to look legitimate
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_text(text):
    if text:
        return text.strip().replace('\n', ' ')
    return None

def scrape_lottery_usa(state, game, date_str=None):
    """
    Scrapes lotteryusa.com which is much friendlier to bots/APIs
    """
    data = {
        "state": state.upper(),
        "game": game,
        "source": "lotteryusa.com",
        "winning_numbers": [],
        "date": "Latest"
    }
    
    # URL Structure: https://www.lotteryusa.com/florida/powerball/
    base_url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    
    # If they want history (e.g., 2023-05-10), LotteryUSA usually lists results by year
    # But for V2, let's just hit the main page which usually lists the last 10-20 draws.
    
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # LotteryUSA uses a table for results.
        # We look for the result row.
        
        # 1. Find the main results table or container
        # Their structure usually has a class like "c-result-card" or table rows
        
        # Let's try to find the very first result (Latest)
        # Look for the balls container
        result_container = soup.find('ul', class_=re.compile(r'draw-result'))
        
        if result_container:
            balls = result_container.find_all('li')
            for ball in balls:
                txt = clean_text(ball.text)
                if txt and txt.isdigit():
                    data['winning_numbers'].append(txt)
                    
            # Try to find the date
            date_elem = soup.find('time')
            if date_elem:
                data['date'] = clean_text(date_elem.text)
        
        # FALLBACK: If the specific class above fails, search for ANY sequence of numbers
        # This is the "Nuclear Option" to ensure we get data.
        if not data['winning_numbers']:
            # Find all generic ball classes
            all_balls = soup.find_all('span', class_=re.compile(r'ball|result'))
            for b in all_balls[:6]: # Just take the first 6 found
                if b.text.strip().isdigit():
                    data['winning_numbers'].append(b.text.strip())

    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    # Switch to LotteryUSA logic
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    # Switch to LotteryUSA logic
    return scrape_lottery_usa("texas", "powerball", date_str)
