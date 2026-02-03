from fastapi import FastAPI
from scraper import get_florida_data, get_texas_data
from typing import Optional

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Lottery API V2 is Online",
        "endpoints": [
            "/api/florida?date=YYYY-MM-DD",
            "/api/texas?date=YYYY-MM-DD"
        ]
    }

@app.get("/api/florida")
def read_florida(date: Optional[str] = None):
    return get_florida_data(date)

@app.get("/api/texas")
def read_texas(date: Optional[str] = None):
    return get_texas_data(date)
