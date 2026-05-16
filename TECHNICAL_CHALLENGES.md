# Technical Challenges & Solutions

This document outlines the major technical hurdles encountered during the development of the Charger Tracker and how they were resolved.

## 1. SPA Hydration & State Management
**Challenge:** The target site is a heavy Ionic/Angular Single Page Application. Navigating directly to a station details URL often resulted in a blank "STATION DETAILS" page or a redirect to the provider selection screen because the necessary session state in `IndexedDB` was missing.

**Solution:** I implemented a "Double-Load" and "Flow Control" strategy. The scraper first navigates to the root URL to prime the application, detects if a redirect to `/settings` occurs, automatically selects the "Erlanger Stadtwerke" provider, and then re-navigates to the specific station. This ensures the app's internal state is correctly initialized before data extraction.

## 2. Piercing the Shadow DOM
**Challenge:** Modern Ionic components rely heavily on the Shadow DOM to encapsulate styles and structure. Standard web scrapers and simple `innerText` lookups frequently missed the availability markers (`0/1`, `1/1`) because they were nested inside multiple layers of shadow roots.

**Solution:** I developed a recursive `TreeWalker` script executed within the browser context. This script manually traverses every element in the DOM; if an element has a `shadowRoot`, the script recurses into it. This approach guarantees that no text node, regardless of its encapsulation level, is overlooked.

## 3. UI Obstacles & Modals
**Challenge:** On load, the site frequently displays "Verstanden" (Understood) modals, loading spinners, and side menus (like the filter menu) that can overlay or even prevent the rendering of the charger list.

**Solution:** The scraper was updated with an aggressive cleanup routine. At each cycle of the scraping loop, it searches for and clicks any "Verstanden" or "OK" buttons and forcibly removes `ion-loading`, `ion-backdrop`, and `ion-menu` elements from the DOM. This "clears the stage" for the hydration of the actual charger data.

## 4. Availability Data Association
**Challenge:** The Charger ID (e.g., `DE*LVP...`) and its availability marker (`1/1`) are often in separate text nodes. Simply finding the text "1/1" on a page with multiple connectors is not enough; it must be associated with the correct ID.

**Solution:** I implemented a sequence-based proximity scan. During the DOM traversal, the scraper identifies all "interesting" nodes (IDs and markers). Because of how the SPA renders the list, these nodes appear in a predictable sequence. The scraper tracks the "current" ID and associates the subsequent status marker with it, ensuring accurate mapping for stations with multiple connectors.

## 5. Docker Build & Dependency Conflicts
**Challenge:** The initial Docker build failed due to a missing `requirements.txt` and a missing `python-multipart` dependency required by FastAPI to handle the "Add Station" form data.

**Solution:** I created a comprehensive `requirements.txt` including all necessary libraries (`fastapi`, `uvicorn`, `jinja2`, `playwright`, `python-multipart`). I also verified the `Dockerfile` to ensure it correctly installed both the Python packages and the Playwright system dependencies (Chromium) in a single, consistent build layer.
