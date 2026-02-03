from fastapi import FastAPI
from scraper import get_all_lotto_data, get_florida_data, get_texas_data

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Lottery API is Online",
        "usage": "Go to /api/all, /api/florida, or /api/texas"
    }

@app.get("/api/all")
def read_all():
    # This calls the scraper immediately when requested
    return get_all_lotto_data()

@app.get("/api/florida")
def read_florida():
    return get_florida_data()

@app.get("/api/texas")
def read_texas():
    return get_texas_data()
