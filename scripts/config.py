# Only games that are scraped from lottery.net
# PDF games (pick-2, pick-3, pick-4, pick-5, cash4life) are handled separately

GAMES = {
    "powerball": {
        "name": "Powerball",
        "state": "florida",
        "numbers_count": 6,
        "draw_times": ["evening"],
        "source_type": "lottery_net_national",
        "lottery_net_slug": "powerball"
    },
    "mega-millions": {
        "name": "Mega Millions",
        "state": "florida",
        "numbers_count": 6,
        "draw_times": ["evening"],
        "source_type": "lottery_net_national",
        "lottery_net_slug": "mega-millions"
    },
    "florida-lotto": {
        "name": "Florida Lotto",
        "state": "florida",
        "numbers_count": 6,
        "draw_times": ["evening"],
        "source_type": "lottery_net_state",
        "lottery_net_slug": "florida/lotto"
    },
    "fantasy-5": {
        "name": "Fantasy 5",
        "state": "florida",
        "numbers_count": 5,
        "draw_times": ["evening"],
        "source_type": "lottery_net_state",
        "lottery_net_slug": "florida/fantasy-5"
    }
}
