from fastapi import FastAPI
from scraper import get_lotto_data
from typing import Optional

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Lottery API V11 (Master Config)",
        "supported_games": [
            "powerball", "mega-millions", "florida-lotto", 
            "cash4life", "jackpot-triple-play", 
            "pick-2", "pick-3", "pick-4", "pick-5", "fantasy-5"
        ],
        "usage": "/api/{state}/{game}?date=YYYY-MM-DD"
    }

@app.get("/api/{state}/{game}")
def read_lotto(state: str, game: str, date: Optional[str] = None):
    return get_lotto_data(state, game, date)
