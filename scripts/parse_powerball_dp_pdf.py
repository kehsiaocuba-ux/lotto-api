#!/usr/bin/env python3
"""
Parse Florida Lottery Powerball Double Play PDF.
Format: M/D/YY NUM NUM NUM NUM NUM PB NUM POWERBALL DP
We only want POWERBALL DP rows (Double Play)
"""

import pdfplumber
import re
import json
import os
from datetime import datetime

# Pattern: 2/7/26 28 37 38 48 63 PB 14 POWERBALL DP
PATTERN = re.compile(
    r'(\d{1,2}/\d{1,2}/\d{2})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+PB\s+(\d+)\s+POWERBALL\s+DP'
)


def parse_date(date_str):
    """Parse '2/7/26' into '2026-02-07'"""
    parts = date_str.split('/')
    month = int(parts[0])
    day = int(parts[1])
    year = int(parts[2])
    
    if year < 100:
        if year > 50:
            year = 1900 + year
        else:
            year = 2000 + year
    
    return f"{year}-{month:02d}-{day:02d}"


def parse_pdf(pdf_path):
    """Parse Powerball PDF and extract Double Play draws."""
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
                numbers = list(match[1:6])  # 5 white balls
                powerball = match[6]
                
                try:
                    date_str = parse_date(date_raw)
                    
                    if date_str in seen:
                        continue
                    seen.add(date_str)
                    
                    all_numbers = numbers + [powerball]
                    
                    draws.append({
                        "date": date_str,
                        "draw_time": "evening",
                        "numbers": all_numbers
                    })
                    
                except Exception as e:
                    print(f"  Error parsing: {match} - {e}")
                    continue
    
    draws.sort(key=lambda x: x["date"], reverse=True)
    
    print(f"  Found {len(draws)} draws")
    return draws


def main():
    pdf_path = os.path.expanduser("~/Downloads/test_pb.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    
    print("=" * 50)
    print("Powerball Double Play PDF Parser")
    print("=" * 50)
    
    draws = parse_pdf(pdf_path)
    
    if draws:
        json_data = {
            "game": "powerball-double-play",
            "game_name": "Powerball Double Play",
            "state": "florida",
            "numbers_count": 6,
            "draw_times": ["evening"],
            "last_updated": datetime.now().isoformat() + "Z",
            "total_draws": len(draws),
            "draws": draws
        }
        
        output_file = os.path.join(data_dir, "florida_powerball-double-play.json")
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"  Saved to: {output_file}")
        print(f"  Latest: {draws[0]['date']} - {draws[0]['numbers']}")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
