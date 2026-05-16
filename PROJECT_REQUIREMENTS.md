# Project Requirements Summary

This document summarizes the requirements gathered for the Charger Tracker project.

## 1. Core Objective
Develop a automated system to monitor the availability of EV charging stations from the LadeVerbundPlus (ChargeCloud) network, as the provider does not offer a public API.

## 2. Scraping Requirements
- **Target URL:** Primary focus on `https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583`.
- **Frequency:** The system must check the status every 5 minutes.
- **Data Points:**
    - Charger ID (e.g., `DE*LVP*E21065*001`).
    - Availability Status: Must specifically capture the `0/1` (Occupied) and `1/1` (Available) markers shown on the website.
- **Robustness:** The scraper must handle the dynamic nature of the target Single Page App (SPA), including hydration delays and Shadow DOM structures.

## 3. Backend Requirements
- **Technology:** Python-based backend using **FastAPI**.
- **Task Management:** Background scraping loop to update data independently of user requests.
- **Integration API:** Provide a `/status` endpoint returning data in JSON format for home automation systems (e.g., FHEM).
- **Multi-Station Support:** Support for tracking multiple charging stations simultaneously by their ID.

## 4. Frontend Requirements
- **Dashboard:** A web-based UI to display the status of all tracked chargers.
- **UI Elements:**
    - Visual status badges (Green for Available, Red for Occupied).
    - Connector-level details.
    - German-formatted timestamps for the last successful update (`HH:MMh at DD.MM.YYYY`).
    - Management tools: Manual refresh trigger, ability to add and remove stations.
    - Loading indicators during background or manual scrapes.

## 5. Persistence & Infrastructure
- **Persistence:** Tracked station IDs must be persisted across application restarts (implemented via CSV in the project).
- **Deployment:** The application must be fully dockerized for easy deployment and consistent execution of browser dependencies (Playwright).
- **Configuration:** Core settings (intervals, provider names) should be configurable via environment variables.
