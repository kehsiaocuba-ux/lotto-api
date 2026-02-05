import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}


def parse_date_from_text(text: str) -> Optional[str]:
    text = text.strip()
    
    match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', text)
    if match:
        month_str = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3))
        month = MONTH_MAP.get(month_str) or MONTH_MAP.get(month_str[:3])
        if month:
            return f"{year}-{month:02d}-{day:02d}"
    
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        return f"{year}-{month:02d}-{day:02d}"
    
    return None


def extract_numbers_from_row(row, limit: int) -> List[str]:
    numbers = []
    
    balls = row.find_all('li')
    for ball in balls:
        text = ball.get_text(strip=True)
        if re.match(r'^\d+$', text):
            numbers.append(text)
            if len(numbers) >= limit:
                break
    
    if len(numbers) < limit:
        cells = row.find_all(['td', 'span'])
        for cell in cells:
            text = cell.get_text(strip=True)
            if re.match(r'^\d+$', text) and text not in numbers:
                numbers.append(text)
                if len(numbers) >= limit:
                    break
    
    return numbers[:limit]


def scrape_lottery_net_year(game_slug: str, year: int, numbers_count: int) -> List[Dict]:
    url = f"https://www.lottery.net/{game_slug}/numbers/{year}"
    print(f"    Fetching: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"    Error: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'lxml')
    results = []
    
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            if row.find('th'):
                continue
            
            row_text = row.get_text()
            date_str = parse_date_from_text(row_text)
            
            if not date_str:
                continue
            
            numbers = extract_numbers_from_row(row, numbers_count)
            
            if len(numbers) >= numbers_count:
                draw_time = "midday" if "midday" in row_text.lower() else "evening"
                results.append({
                    "date": date_str,
                    "draw_time": draw_time,
                    "numbers": numbers
                })
    
    print(f"    Found {len(results)} draws for {year}")
    return results


def scrape_game_history(game_slug: str, numbers_count: int, months_back: int = 6) -> List[Dict]:
    all_results = []
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    years_to_scrape = {current_year}
    check_month = current_month - months_back
    check_year = current_year
    while check_month <= 0:
        check_month += 12
        check_year -= 1
        years_to_scrape.add(check_year)
    
    for year in sorted(years_to_scrape, reverse=True):
        year_results = scrape_lottery_net_year(game_slug, year, numbers_count)
        all_results.extend(year_results)
        time.sleep(1)
    
    cutoff_year = current_year
    cutoff_month = current_month - months_back
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_str = f"{cutoff_year}-{cutoff_month:02d}-01"
    
    filtered = [r for r in all_results if r["date"] >= cutoff_str]
    filtered.sort(key=lambda x: x["date"], reverse=True)
    
    seen = set()
    unique = []
    for r in filtered:
        key = (r["date"], r["draw_time"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique
