# Charging Station Scraper

A small backend to scrape the status of a specific charging station from ChargeCloud and display it via a simple HTML frontend or a JSON API.

## Features
- Scrapes charging status every 5 minutes (configurable).
- Handles "Erlanger Stadtwerke" provider selection.
- Provides a JSON endpoint at `/status` for FHEM integration.
- Simple HTML frontend at `/`.
- Dockerized for easy deployment on a Raspberry Pi.

## Configuration
Use the following environment variables:
- `SCRAPE_INTERVAL`: Interval in seconds (default: 300).
- `STATION_URL`: URL of the charging station.
- `PROVIDER_NAME`: Name of the provider to select (default: "Erlanger Stadtwerke").

## Running with Docker
```bash
docker build -t charger-scraper .
docker run -d -p 8000:8000 --name charger-scraper charger-scraper
```
