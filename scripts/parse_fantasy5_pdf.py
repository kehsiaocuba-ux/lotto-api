#!/usr/bin/env python3
"""
Parse Florida Lottery Fantasy 5 PDF (ff.pdf).
Format: M/D/YY EVENING/MIDDAY # # # # #
Has both midday and evening draws.
"""

import pdfplumber
import re
import json
import os
from datetime import datetime

# Pattern: 2/8/26 EVENING 4 8 11 34 35
PATTERN = re.compile(
    r'(\d{1,2}/\d{1,2}/\d{2})\s+(EVENING|MIDDAY)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'
)


def parse_date(date_str):
    """Parse '2/8/26' into '2026-02-08'"""
    parts = date_str.split('/')
    month = int(parts[0])
    day = int(parts[1])
    year = int(parts[2])
    
    # Handle 2-digit year: 00-50 = 2000s, 51-99 = 1900s
    if year < 100:
        if year > 50:
            year = 1900 + year
        else:
            year = 2000 + year
    
    return f"{year}-{month:02d}-{day:02d}"


def parse_pdf(pdf_path):
    """Parse Fantasy 5 PDF and extract all draws."""
    print(f"Parsing: {pdf_path}")
    
    draws = []
    seen = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            matches = PATTERN.findall(text)
            
            for match in matches:
                date_raw = match[0]
                draw_type = match[1].lower()
                numbers = list(match[2:7])
                
                try:
                    date_str = parse_date(date_raw)
                    
                    key = (date_str, draw_type)
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    draws.append({
                        "date": date_str,
                        "draw_time": draw_type,
                        "numbers": numbers
                    })
                    
                except Exception as e:
                    print(f"  Error parsing: {match} - {e}")
                    continue
    
    draws.sort(key=lambda x: (x["date"], x["draw_time"]), reverse=True)
    
    print(f"  Found {len(draws)} draws")
    return draws


def main():
    pdf_path = os.path.expanduser("~/Downloads/test_ff.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    
    print("=" * 50)
    print("Fantasy 5 PDF Parser")
    print("=" * 50)
    
    draws = parse_pdf(pdf_path)
    
    if draws:
        json_data = {
            "game": "fantasy-5",
            "game_name": "Fantasy 5",
            "state": "florida",
            "numbers_count": 5,
            "draw_times": ["midday", "evening"],
            "last_updated": datetime.now().isoformat() + "Z",
            "total_draws": len(draws),
            "draws": draws
        }
        
        output_file = os.path.join(data_dir, "florida_fantasy-5.json")
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"  Saved to: {output_file}")
        print(f"  Latest: {draws[0]['date']} {draws[0]['draw_time']} - {draws[0]['numbers']}")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
