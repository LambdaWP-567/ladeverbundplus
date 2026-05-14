# Charger Status Scraper & Backend

A small FastAPI backend that scrapes the ChargeCloud website for a specific charging station's status and provides a JSON API and a simple web frontend.

## Features
- Scrapes the highly dynamic Ionic/Angular SPA using Playwright.
- Handles provider selection automatically.
- Provides a `/status` JSON endpoint for home automation (e.g., FHEM).
- Simple HTML frontend showing the current status.
- Dockerized for easy deployment on a Raspberry Pi.

## Environment Variables
- `SCRAPE_INTERVAL`: Interval in seconds between scrapes (default: 300).
- `STATION_URL`: The URL of the charging station on ChargeCloud.
- `PROVIDER_NAME`: The name of the provider to select (default: "Erlanger Stadtwerke").

## Running locally
1. Install dependencies: `pip install -r requirements.txt`
2. Install Playwright browsers: `playwright install chromium`
3. Start the server: `python main.py`

## Docker
The image is built and pushed to GHCR via GitHub Actions.
To run manually:
```bash
docker build -t charger-status .
docker run -p 8000:8000 charger-status
```
