import requests
from bs4 import BeautifulSoup
import re

# HEADERS are needed to prevent the websites from blocking us
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def clean_text(text):
    if text:
        return text.strip().replace('\n', ' ')
    return None

def get_florida_data():
    # Targeted scraping for Florida Powerball (Example)
    # You will need to duplicate this logic for MegaMillions, etc.
    url = "https://www.flalottery.com/powerball"
    data = {
        "state": "FL",
        "game": "Powerball",
        "last_draw_date": None,
        "winning_numbers": [],
        "next_draw_date": None,
        "next_jackpot": None,
        "winners_info": "Not available in simple view",
        "winning_location": "See official site" 
    }
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # NOTE: CSS Selectors below are educated guesses based on standard structures.
        # If the website updates, these selectors must be updated.
        
        # Attempt to find the Game Header/Numbers
        # This part requires inspecting the specific FL Lottery HTML structure
        # Below is a generic structure usually found on these sites
        
        # Example extraction logic:
        game_content = soup.find('div', {'class': 'gamePage-header'}) 
        if game_content:
            # Try to find date
            date_elem = game_content.find('p', {'class': 'draw-date'})
            if date_elem:
                data['last_draw_date'] = clean_text(date_elem.text)

            # Try to find numbers (balls)
            balls = game_content.find_all('span', {'class': 'ball'})
            for ball in balls:
                data['winning_numbers'].append(clean_text(ball.text))

        # Attempt to find Next Jackpot
        jackpot_elem = soup.find('span', {'class': 'next-jackpot-amount'})
        if jackpot_elem:
            data['next_jackpot'] = clean_text(jackpot_elem.text)
            
    except Exception as e:
        data['error'] = str(e)

    return data

def get_texas_data():
    url = "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/index.html"
    data = {
        "state": "TX",
        "game": "Powerball",
        "last_draw_date": None,
        "winning_numbers": [],
        "next_jackpot": None
    }
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Texas usually puts current numbers in a table structure
        # Pseudo-code for extraction:
        blocks = soup.find_all('div', {'class': 'large-balls'})
        if blocks:
             for block in blocks:
                 data['winning_numbers'].append(clean_text(block.text))
                 
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_all_lotto_data():
    return {
        "florida": get_florida_data(),
        "texas": get_texas_data()
    }
