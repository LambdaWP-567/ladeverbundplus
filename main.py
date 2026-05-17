from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import asyncio
import os
import csv
from scraper import ChargerScraper
from datetime import datetime
from typing import Dict, List

VERSION = "1.3.0"
DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "stations.csv")
STATION_BASE_URL = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/"
DEFAULT_STATION_ID = "3411583"
PROVIDER_NAME = os.getenv("PROVIDER_NAME", "Erlanger Stadtwerke")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", 300))
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"

# Global state
charger_data: Dict[str, dict] = {}
stations: List[str] = []
is_scraping = False

def load_stations():
    global stations
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        stations = [DEFAULT_STATION_ID]
        save_stations()
    else:
        with open(CSV_PATH, "r") as f:
            reader = csv.reader(f)
            stations = [row[0] for row in reader if row]

    # Initialize charger_data for new stations
    for sid in stations:
        if sid not in charger_data:
            charger_data[sid] = {
                "status": "Starting",
                "connectors": [],
                "last_updated": None,
                "error": "Start up phase"
            }

def save_stations():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        for sid in stations:
            writer.writerow([sid])

async def perform_scrape_all():
    global charger_data, is_scraping
    if is_scraping:
        return
    is_scraping = True
    try:
        # Create a copy of stations to avoid mutation during iteration if someone adds one
        current_stations = list(stations)
        for sid in current_stations:
            url = f"{STATION_BASE_URL}{sid}"
            scraper = ChargerScraper(url, PROVIDER_NAME, verbose=VERBOSE_LOGGING)
            print(f"[{datetime.now()}] Scraping station {sid}...")
            try:
                result = await scraper.scrape()
                charger_data[sid] = result
            except Exception as e:
                print(f"[{datetime.now()}] Error scraping {sid}: {e}")
                if sid not in charger_data: charger_data[sid] = {}
                charger_data[sid]["status"] = "Error"
                charger_data[sid]["error"] = str(e)
                charger_data[sid]["last_updated"] = datetime.now().isoformat()
    finally:
        is_scraping = False

async def update_status_loop():
    while True:
        await perform_scrape_all()
        await asyncio.sleep(SCRAPE_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.now()}] STARTING CHARGER STATUS APP VERSION {VERSION}")
    load_stations()
    task = asyncio.create_task(update_status_loop())
    yield
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
        return str(ts_str)

templates.env.filters["german_ts"] = format_timestamp

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "charger_data": charger_data,
            "is_scraping": is_scraping,
            "version": VERSION
        }
    )

@app.post("/add")
async def add_station(station_id: str = Form(...)):
    sid = station_id.strip()
    if sid and sid not in stations:
        stations.append(sid)
        save_stations()
        charger_data[sid] = {"status": "Starting", "connectors": [], "last_updated": None, "error": "Added"}
        # Trigger an immediate background scrape
        await perform_scrape_all()
    return RedirectResponse(url="/", status_code=303)

@app.get("/remove/{station_id}")
async def remove_station(station_id: str):
    if station_id in stations:
        stations.remove(station_id)
        save_stations()
        if station_id in charger_data:
            del charger_data[station_id]
    return RedirectResponse(url="/", status_code=303)

@app.get("/status")
async def get_status():
    return JSONResponse(content={
        "version": VERSION,
        "stations": charger_data,
        "is_scraping": is_scraping
    })

@app.get("/refresh")
async def refresh_data():
    await perform_scrape_all()
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
