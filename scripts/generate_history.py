#!/usr/bin/env python3
import json
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.config import GAMES
from scripts.scraper_local import scrape_game_history

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def generate_game_history(game_id: str, game_config: dict, months_back: int = 6) -> bool:
    print(f"\n{'='*50}")
    print(f"Processing: {game_config['name']}")
    print(f"{'='*50}")
    
    slug = game_config["lottery_net_slug"]
    numbers_count = game_config["numbers_count"]
    
    try:
        draws = scrape_game_history(slug, numbers_count, months_back)
    except Exception as e:
        print(f"  Error: {e}")
        return False
    
    if not draws:
        print(f"  No results found")
        return False
    
    output = {
        "game": game_id,
        "game_name": game_config["name"],
        "state": game_config["state"],
        "numbers_count": numbers_count,
        "draw_times": game_config["draw_times"],
        "last_updated": datetime.now().isoformat() + "Z",
        "total_draws": len(draws),
        "draws": draws
    }
    
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = f"{game_config['state']}_{game_id}.json"
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"  Saved {len(draws)} draws to {filename}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate lottery history")
    parser.add_argument("--game", type=str, help="Single game to generate")
    parser.add_argument("--months", type=int, default=6, help="Months of history")
    args = parser.parse_args()
    
    print("Lottery History Generator")
    print(f"Fetching {args.months} months of history")
    
    if args.game:
        if args.game not in GAMES:
            print(f"Unknown game: {args.game}")
            print(f"Available: {', '.join(GAMES.keys())}")
            sys.exit(1)
        generate_game_history(args.game, GAMES[args.game], args.months)
    else:
        for game_id, config in GAMES.items():
            generate_game_history(game_id, config, args.months)


if __name__ == "__main__":
    main()
