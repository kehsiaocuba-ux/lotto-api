#!/usr/bin/env python3
"""
Parse Florida Lottery PDF files and convert to JSON.
Handles Pick 2, Pick 3, Pick 4, and Pick 5.
"""

import pdfplumber
import re
import json
import os
from datetime import datetime

# Pattern: MM/DD/YY E/M #-#-#... FB# or FB #
# Handles both "FB5" and "FB 5" formats
PATTERN = re.compile(
    r'(\d{2}/\d{2}/\d{2})\s+([EM])\s+([\d\-\s]+?)\s*FB\s*(\d+)'
)


def parse_numbers(num_str, expected_count):
    """Parse '9- 4- 3- 8- 1' into ['9', '4', '3', '8', '1']"""
    numbers = re.findall(r'\d+', num_str)
    return numbers[:expected_count]


def parse_date(date_str):
    """Parse '02/05/26' into '2026-02-05'"""
    parts = date_str.split('/')
    month = int(parts[0])
    day = int(parts[1])
    year = int(parts[2])
    
    if year < 100:
        year = 2000 + year
    
    return f"{year}-{month:02d}-{day:02d}"


def parse_pdf(pdf_path, game_name, numbers_count):
    """Parse a lottery PDF and extract all draws."""
    print(f"Parsing: {pdf_path}")
    
    draws = []
    seen = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            matches = PATTERN.findall(text)
            
            for match in matches:
                date_raw, draw_time_code, numbers_raw, fireball = match
                
                try:
                    date_str = parse_date(date_raw)
                    draw_time = "evening" if draw_time_code == "E" else "midday"
                    numbers = parse_numbers(numbers_raw, numbers_count)
                    
                    if len(numbers) < numbers_count:
                        continue
                    
                    key = (date_str, draw_time)
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    draws.append({
                        "date": date_str,
                        "draw_time": draw_time,
                        "numbers": numbers,
                        "fireball": fireball
                    })
                    
                except Exception as e:
                    print(f"  Error parsing: {match} - {e}")
                    continue
    
    draws.sort(key=lambda x: (x["date"], x["draw_time"]), reverse=True)
    
    print(f"  Found {len(draws)} draws")
    return draws


def create_game_json(draws, game_id, game_name, numbers_count):
    """Create the JSON structure for a game."""
    return {
        "game": game_id,
        "game_name": game_name,
        "state": "florida",
        "numbers_count": numbers_count,
        "draw_times": ["midday", "evening"],
        "has_fireball": True,
        "last_updated": datetime.now().isoformat() + "Z",
        "total_draws": len(draws),
        "draws": draws
    }


def main():
    games = [
        {
            "pdf": os.path.expanduser("~/Downloads/pick2.pdf"),
            "game_id": "pick-2",
            "game_name": "Pick 2",
            "numbers_count": 2
        },
        {
            "pdf": os.path.expanduser("~/Downloads/pick3.pdf"),
            "game_id": "pick-3",
            "game_name": "Pick 3",
            "numbers_count": 3
        },
        {
            "pdf": os.path.expanduser("~/Downloads/pick4.pdf"),
            "game_id": "pick-4",
            "game_name": "Pick 4",
            "numbers_count": 4
        },
        {
            "pdf": os.path.expanduser("~/Downloads/pick5.pdf"),
            "game_id": "pick-5",
            "game_name": "Pick 5",
            "numbers_count": 5
        }
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("=" * 50)
    print("Florida Lottery PDF Parser")
    print("=" * 50)
    
    for game in games:
        pdf_path = game["pdf"]
        
        if not os.path.exists(pdf_path):
            print(f"\nSkipping {game['game_name']}: PDF not found")
            continue
        
        print(f"\n{'='*50}")
        print(f"Processing: {game['game_name']}")
        print(f"{'='*50}")
        
        draws = parse_pdf(pdf_path, game["game_name"], game["numbers_count"])
        
        if draws:
            json_data = create_game_json(
                draws, 
                game["game_id"], 
                game["game_name"], 
                game["numbers_count"]
            )
            
            output_file = os.path.join(data_dir, f"florida_{game['game_id']}.json")
            with open(output_file, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            print(f"  Saved to: {output_file}")
            
            if draws:
                print(f"  Latest: {draws[0]['date']} {draws[0]['draw_time']} - {draws[0]['numbers']}")
    
    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
