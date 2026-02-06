#!/usr/bin/env python3
"""
Parse Florida Lottery Cash4Life PDF and convert to JSON.
Format: MM/DD/YY #- #- #- #- # CB #
"""

import pdfplumber
import re
import json
import os
from datetime import datetime

# Pattern: MM/DD/YY #- #- #- #- # CB #
# Example: 02/05/26 13- 21- 22- 47- 48 CB 4
PATTERN = re.compile(
    r'(\d{2}/\d{2}/\d{2})\s+([\d\-\s]+?)\s*CB\s*(\d+)'
)


def parse_numbers(num_str):
    """Parse '13- 21- 22- 47- 48' into ['13', '21', '22', '47', '48']"""
    numbers = re.findall(r'\d+', num_str)
    return numbers[:5]  # Cash4Life has 5 main numbers


def parse_date(date_str):
    """Parse '02/05/26' into '2026-02-05'"""
    parts = date_str.split('/')
    month = int(parts[0])
    day = int(parts[1])
    year = int(parts[2])
    
    if year < 100:
        year = 2000 + year
    
    return f"{year}-{month:02d}-{day:02d}"


def parse_pdf(pdf_path):
    """Parse Cash4Life PDF and extract all draws."""
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
                date_raw, numbers_raw, cashball = match
                
                try:
                    date_str = parse_date(date_raw)
                    numbers = parse_numbers(numbers_raw)
                    
                    # Cash4Life needs 5 numbers
                    if len(numbers) < 5:
                        continue
                    
                    # Skip duplicates
                    if date_str in seen:
                        continue
                    seen.add(date_str)
                    
                    # Add cashball as 6th number (like Powerball's red ball)
                    all_numbers = numbers + [cashball]
                    
                    draws.append({
                        "date": date_str,
                        "draw_time": "evening",
                        "numbers": all_numbers,
                        "cashball": cashball
                    })
                    
                except Exception as e:
                    print(f"  Error parsing: {match} - {e}")
                    continue
    
    draws.sort(key=lambda x: x["date"], reverse=True)
    
    print(f"  Found {len(draws)} draws")
    return draws


def main():
    pdf_path = os.path.expanduser("~/Downloads/cash4life.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("=" * 50)
    print("Cash4Life PDF Parser")
    print("=" * 50)
    
    draws = parse_pdf(pdf_path)
    
    if draws:
        json_data = {
            "game": "cash4life",
            "game_name": "Cash4Life",
            "state": "florida",
            "numbers_count": 6,  # 5 main + 1 cash ball
            "draw_times": ["evening"],
            "has_cashball": True,
            "last_updated": datetime.now().isoformat() + "Z",
            "total_draws": len(draws),
            "draws": draws
        }
        
        output_file = os.path.join(data_dir, "florida_cash4life.json")
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"  Saved to: {output_file}")
        print(f"  Latest: {draws[0]['date']} - {draws[0]['numbers']}")
    
    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
