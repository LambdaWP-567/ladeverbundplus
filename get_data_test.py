
import asyncio
from playwright.async_api import async_playwright
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_charger_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a realistic User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'

        logger.info("Loading page (1st time)...")
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(5000)

        if await page.query_selector('ion-title:has-text("PROVIDER")'):
            logger.info("Provider selection detected. Selecting Erlanger Stadtwerke...")
            await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('ion-item');
                    for (const item of items) {
                        if (item.innerText.includes('Erlanger Stadtwerke')) {
                            item.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            await page.wait_for_timeout(5000)
            logger.info("Reloading page (2nd time)...")
            await page.goto(url, wait_until="load")

        logger.info("Waiting for loading spinners to disappear...")
        # Wait for all ion-loading elements to be hidden or gone
        try:
            await page.wait_for_function("""
                () => document.querySelectorAll('ion-loading').length === 0 ||
                      Array.from(document.querySelectorAll('ion-loading')).every(el => el.offsetParent === null)
            """, timeout=60000)
            logger.info("Loading spinners are gone.")
        except Exception as e:
            logger.warning(f"Timeout waiting for spinners to disappear: {e}")

        # Final wait for any JS to settle
        await page.wait_for_timeout(10000)

        logger.info("Extracting data...")

        # Capture screenshot for verification
        await page.screenshot(path='extraction_debug.png')

        # Get all text and elements
        page_data = await page.evaluate("""
            () => {
                const results = [];
                // Look for cards that contain charger IDs
                const cards = document.querySelectorAll('ion-card, .connector-container, ion-item');
                for (const card of cards) {
                    const text = card.innerText;
                    if (text.includes('DE*LVP')) {
                        results.push({
                            html: card.innerHTML,
                            text: text.replace(/\\n/g, ' ').trim()
                        });
                    }
                }
                return {
                    full_text: document.body.innerText,
                    interesting_items: results
                };
            }
        """)

        logger.info(f"Full Page Text Snippet: {page_data['full_text'][:500]}...")
        logger.info(f"Found {len(page_data['interesting_items'])} interesting items.")

        connectors = []
        for item in page_data['interesting_items']:
            text = item['text']
            # Search for ID pattern DE*LVP*...
            import re
            match = re.search(r'DE\*LVP\*E\d+\*\d+', text)
            cid = match.group(0) if match else "Unknown"

            status = "Unknown"
            if "1/1" in text or "Verfügbar" in text or "Available" in text:
                status = "Available"
            elif "0/1" in text or "Besetzt" in text or "Occupied" in text:
                status = "Occupied"

            ctype = "Type 2" if "Typ 2" in text else "CCS" if "CCS" in text else "Unknown"

            if cid != "Unknown" and not any(c['id'] == cid for c in connectors):
                connectors.append({
                    "id": cid,
                    "type": ctype,
                    "status": status,
                    "raw": text
                })

        logger.info(f"Final Connectors: {connectors}")

        await browser.close()
        return connectors

if __name__ == "__main__":
    asyncio.run(get_charger_data())
