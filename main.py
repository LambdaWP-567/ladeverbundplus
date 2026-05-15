from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import asyncio
import os
from scraper import ChargerScraper
from datetime import datetime

VERSION = "1.0.1 from (15.05.2026)"

# Global state
charger_status = {
    "status": "Starting",
    "connectors": [],
    "last_updated": None,
    "error": "Start up phase"
}

SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 60))
STATION_URL = os.getenv("STATION_URL", "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583")
PROVIDER_NAME = os.getenv("PROVIDER_NAME", "Erlanger Stadtwerke")

scraper_instance = ChargerScraper(STATION_URL, PROVIDER_NAME)

async def perform_scrape():
    global charger_status
    try:
        print(f"[{datetime.now()}] Starting scrape...")
        result = await scraper_instance.scrape()
        charger_status = result
        print(f"[{datetime.now()}] Scrape completed. Status: {charger_status['status']}")
    except Exception as e:
        print(f"[{datetime.now()}] Unexpected error in scrape: {e}")
        charger_status["status"] = "Unknown"
        charger_status["error"] = str(e)
        charger_status["last_updated"] = datetime.now().isoformat()

async def update_status_loop():
    while True:
        await perform_scrape()
        await asyncio.sleep(SCRAPE_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background task
    task = asyncio.create_task(update_status_loop())
    yield
    # Shutdown: Cancel background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

def format_timestamp(ts_str):
    if not ts_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%H:%Mh at %d.%m.%Y")
    except:
        return ts_str

templates.env.filters["german_ts"] = format_timestamp

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": charger_status,
            "now": datetime.now().isoformat(),
            "version": VERSION
        }
    )

@app.get("/status")
async def get_status():
    status_with_version = charger_status.copy()
    status_with_version["version"] = VERSION
    return JSONResponse(content=status_with_version)

@app.get("/refresh")
async def refresh_data():
    await perform_scrape()
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
