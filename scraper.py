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
        "date": date_str if date_str else "Latest"
    }
    
    # 1. Determine URL based on date
    # Base URL: https://www.lotteryusa.com/florida/powerball/
    base_url = f"https://www.lotteryusa.com/{state.lower()}/{game.lower()}/"
    
    target_url = base_url
    
    if date_str:
        # Input format is YYYY-MM-DD (e.g., 2023-10-25)
        # We need to extract the Year to find the correct archive page.
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            year = dt_obj.year
            # LotteryUSA archive structure: .../powerball/2023
            target_url = f"{base_url}{year}"
        except ValueError:
            data['error'] = "Invalid date format. Use YYYY-MM-DD"
            return data
    
    try:
        response = requests.get(target_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # LOGIC A: Fetching a Specific Date
        if date_str:
            # We look for a <time> tag that matches our date string
            # LotteryUSA usually uses <time datetime="2023-10-25">
            target_time = soup.find('time', attrs={'datetime': date_str})
            
            if target_time:
                # The numbers are usually in the same container (row) as the time
                # We go up to the parent row (tr) or container (div)
                row = target_time.find_parent('tr')
                if not row:
                    # Fallback for card layout
                    row = target_time.find_parent('div', class_=re.compile(r'result'))
                
                if row:
                    # Find numbers inside this specific row
                    balls = row.find_all('li')
                    for ball in balls:
                        txt = clean_text(ball.text)
                        if txt and txt.isdigit():
                            data['winning_numbers'].append(txt)
            else:
                data['error'] = "Date not found in archive."

        # LOGIC B: Fetching Latest (No date provided)
        else:
            # Find the first result on the main page
            result_container = soup.find('ul', class_=re.compile(r'draw-result'))
            if result_container:
                balls = result_container.find_all('li')
                for ball in balls:
                    txt = clean_text(ball.text)
                    if txt and txt.isdigit():
                        data['winning_numbers'].append(txt)
                
                # Try to capture the date of this latest draw
                date_elem = soup.find('time')
                if date_elem:
                    data['date'] = clean_text(date_elem.text)

    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_florida_data(date_str=None):
    return scrape_lottery_usa("florida", "powerball", date_str)

def get_texas_data(date_str=None):
    return scrape_lottery_usa("texas", "powerball", date_str)
