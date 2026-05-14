
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import asyncio
import os
from scraper import ChargerScraper
from datetime import datetime
import threading
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Global state
charger_status = {
    "status": "Unknown",
    "connectors": [],
    "last_updated": None,
    "error": "Initializing..."
}

SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 300))
STATION_URL = os.getenv("STATION_URL", "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583")
PROVIDER_NAME = os.getenv("PROVIDER_NAME", "Erlanger Stadtwerke")

async def update_status():
    global charger_status
    scraper = ChargerScraper(STATION_URL, PROVIDER_NAME)
    while True:
        try:
            print(f"[{datetime.now()}] Starting scheduled scrape...")
            result = await scraper.scrape()
            charger_status = result
            print(f"[{datetime.now()}] Scrape completed. Status: {charger_status['status']}")
        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error in background task: {e}")
            charger_status["status"] = "Unknown"
            charger_status["error"] = str(e)
            charger_status["last_updated"] = datetime.now().isoformat()

        await asyncio.sleep(SCRAPE_INTERVAL)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_status())

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "data": charger_status,
        "now": datetime.now().isoformat()
    })

@app.get("/status")
async def get_status():
    return JSONResponse(content=charger_status)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
