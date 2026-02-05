from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json
import os
from datetime import datetime

app = FastAPI(title="Florida Lottery API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GAME_DATA = {}

def load_game_data():
    global GAME_DATA
    if not os.path.exists(DATA_DIR):
        return
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    game_id = data.get('game')
                    if game_id:
                        GAME_DATA[game_id] = data
            except Exception as e:
                print(f"Error loading {filename}: {e}")

load_game_data()


@app.get("/")
async def root():
    return {
        "name": "Florida Lottery API",
        "version": "2.0.0",
        "games_loaded": list(GAME_DATA.keys()),
        "endpoints": {
            "list_games": "GET /api/games",
            "get_results": "GET /api/florida/{game}",
            "get_historical": "GET /api/florida/{game}?date=YYYY-MM-DD",
            "health": "GET /api/health"
        }
    }


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "games_loaded": len(GAME_DATA),
        "games": list(GAME_DATA.keys()),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/games")
async def list_games():
    games = []
    for game_id, data in GAME_DATA.items():
        games.append({
            "id": game_id,
            "name": data.get("game_name", game_id),
            "numbers_count": data.get("numbers_count"),
            "draw_times": data.get("draw_times", ["evening"]),
            "total_draws": data.get("total_draws", 0),
            "last_updated": data.get("last_updated")
        })
    return {"games": games}


@app.get("/api/florida/{game}")
async def get_florida_results(
    game: str,
    date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    draw_time: Optional[str] = Query(None, regex=r"^(midday|evening)$")
):
    game = game.lower()
    
    if game not in GAME_DATA:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Game not found: {game}", "available": list(GAME_DATA.keys())}
        )
    
    game_data = GAME_DATA[game]
    draws = game_data.get("draws", [])
    
    if not draws:
        raise HTTPException(status_code=404, detail={"error": "No draw data available"})
    
    # Latest result
    if not date:
        latest = draws[0]
        return {
            "state": "FLORIDA",
            "game": game,
            "game_name": game_data.get("game_name"),
            "date_requested": "latest",
            "date_drawn": latest["date"],
            "draw_time": latest.get("draw_time", "evening"),
            "source": "history.json",
            "winning_numbers": latest["numbers"]
        }
    
    # Historical lookup
    matching = [d for d in draws if d["date"] == date]
    
    if not matching:
        all_dates = sorted(set(d["date"] for d in draws), reverse=True)[:5]
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"No results for {game} on {date}",
                "closest_dates": all_dates
            }
        )
    
    # Filter by draw_time if specified
    if draw_time:
        filtered = [d for d in matching if d.get("draw_time") == draw_time]
        if filtered:
            matching = filtered
    
    result = matching[0]
    
    response = {
        "state": "FLORIDA",
        "game": game,
        "game_name": game_data.get("game_name"),
        "date_requested": date,
        "date_drawn": result["date"],
        "draw_time": result.get("draw_time", "evening"),
        "source": "history.json",
        "winning_numbers": result["numbers"]
    }
    
    # Include all draws if multiple on same date (midday + evening)
    if len(matching) > 1:
        response["all_draws_on_date"] = matching
    
    return response


@app.get("/api/{state}/{game}")
async def get_state_results(
    state: str,
    game: str,
    date: Optional[str] = Query(None),
    draw_time: Optional[str] = Query(None)
):
    if state.lower() != "florida":
        raise HTTPException(
            status_code=400,
            detail={"error": f"State not supported: {state}", "supported": ["florida"]}
        )
    return await get_florida_results(game, date, draw_time)
