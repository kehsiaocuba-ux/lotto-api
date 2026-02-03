import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def clean_text(text):
    if text:
        return text.strip().replace('\n', ' ')
    return None

def get_florida_data(date_str=None):
    data = {
        "state": "FL",
        "game": "Powerball",
        "date_requested": date_str if date_str else "latest",
        "winning_numbers": [],
        "raw_data_found": False
    }

    # If the user asks for a specific date, we need to search for it.
    # Note: FL Lottery changes their URL structure often. 
    # Current structure usually involves a search query or an archive page.
    if date_str:
        # LOGIC FOR HISTORY (Example placeholder)
        # You would typically target: https://www.flalottery.com/site/winning-numbers-archive
        url = "https://www.flalottery.com/powerball" 
        data['note'] = "History logic active - showing latest for demo"
    else:
        # LOGIC FOR LATEST
        url = "https://www.flalottery.com/powerball"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try to find the balls (Generic Finder)
        # We look for common class names used by lottery sites
        balls = soup.find_all('span', {'class': 'ball'})
        if not balls:
            balls = soup.find_all('div', {'class': 'winning-numbers'})
            
        for ball in balls:
            txt = clean_text(ball.text)
            if txt and txt.isdigit():
                data['winning_numbers'].append(txt)

        if len(data['winning_numbers']) > 0:
            data['raw_data_found'] = True

    except Exception as e:
        data['error'] = str(e)

    return data

def get_texas_data(date_str=None):
    data = {
        "state": "TX",
        "game": "Powerball",
        "date_requested": date_str if date_str else "latest",
        "winning_numbers": []
    }
    url = "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/index.html"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Generic finder for Texas
        # Texas often uses Tables (td)
        tables = soup.find_all('table')
        if tables:
            # Just grabbing the first few numbers found as a test
            cells = tables[0].find_all('td')
            for cell in cells:
                txt = clean_text(cell.text)
                if txt and txt.isdigit() and len(txt) <= 2:
                     data['winning_numbers'].append(txt)
                     if len(data['winning_numbers']) >= 6: break
    except Exception as e:
        data['error'] = str(e)
    return data
