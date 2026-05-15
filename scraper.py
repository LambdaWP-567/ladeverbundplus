import asyncio
from playwright.async_api import async_playwright
import json
import logging
from datetime import datetime
import os
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChargerScraper:
    def __init__(self, url, provider_name="Erlanger Stadtwerke"):
        self.url = url
        self.provider_name = provider_name
        self.status_data = {"status": "Unknown", "connectors": [], "last_updated": None, "error": "Not started"}
        self.user_data_dir = "/tmp/playwright_persistent_session"

    async def scrape(self):
        async with async_playwright() as p:
            browser_context = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await browser_context.new_page()

            try:
                logger.info(f"Navigating to {self.url}")
                await page.goto(self.url, wait_until="load", timeout=60000)
                await page.wait_for_timeout(5000)

                # Handle Initial Screens (Cookies, Intro, Provider)
                for _ in range(3): # Try a few times to clear potential overlays
                    title = await page.evaluate("() => document.querySelector('ion-title') ? document.querySelector('ion-title').innerText : ''")
                    logger.info(f"Current Title: {title}")

                    # 1. Detect and click "Verstanden" or "Accept" or "OK" for cookies/intro
                    clicked_overlay = await page.evaluate("""
                        () => {
                            const words = ["Verstanden", "OK", "Zustimmen", "Accept", "Schließen", "Close"];
                            const buttons = Array.from(document.querySelectorAll('button, ion-button, span, div'))
                                .filter(el => {
                                    const style = window.getComputedStyle(el);
                                    return style.display !== 'none' && style.visibility !== 'hidden';
                                });

                            for (const btn of buttons) {
                                if (words.some(w => btn.innerText && btn.innerText.includes(w))) {
                                    // Check if it's likely a modal button
                                    const zIndex = window.getComputedStyle(btn).zIndex;
                                    if (zIndex > 100 || btn.closest('ion-modal') || btn.closest('.modal-wrapper')) {
                                        btn.click();
                                        return btn.innerText;
                                    }
                                }
                            }
                            return null;
                        }
                    """)
                    if clicked_overlay:
                        logger.info(f"Clicked overlay button: {clicked_overlay}")
                        await page.wait_for_timeout(2000)
                        continue

                    # 2. Provider selection
                    if "PROVIDER" in title:
                        logger.info("Provider selection screen detected.")
                        await page.evaluate("() => document.querySelectorAll('ion-backdrop, ion-loading').forEach(el => el.remove())")
                        try:
                            await page.click(f"ion-item:has-text('{self.provider_name}')", force=True, timeout=5000)
                            logger.info(f"Clicked '{self.provider_name}'.")
                            await page.wait_for_timeout(5000)
                        except:
                            await page.evaluate(f"""
                                (name) => {{
                                    const items = Array.from(document.querySelectorAll('ion-item'));
                                    const target = items.find(i => i.innerText && i.innerText.includes(name));
                                    if (target) target.click();
                                }}
                            """, self.provider_name)
                            await page.wait_for_timeout(5000)

                        logger.info("Reloading target URL after provider selection...")
                        await page.goto(self.url, wait_until="load")
                        await page.wait_for_timeout(10000)
                        continue

                    break # No more known overlays

                # Extraction
                found_connectors = []
                for attempt in range(1, 11):
                    logger.info(f"Attempt {attempt}: Extracting data...")

                    if "details" not in page.url and attempt > 1:
                        logger.info(f"URL diverted to {page.url}. Re-navigating to {self.url}...")
                        await page.goto(self.url, wait_until="load")
                        await page.wait_for_timeout(5000)

                    connectors = await page.evaluate("""
                        () => {
                            const results = [];
                            function walk(node) {
                                // Search for DE*LVP in the text of this node
                                if (node.innerText && node.innerText.includes('DE*LVP')) {
                                    // We look for the most specific element containing the ID to avoid duplicates
                                    // However, the card contains both the ID and the status.
                                    // Let's try to find cards or items.
                                    const text = node.innerText;
                                    // Regex update: match full ID including multiple stars
                                    const idMatches = text.match(/DE\\*LVP\\*[^*\\s\\n]+(\\*[^*\\s\\n]+)*/g);

                                    if (idMatches) {
                                        for (const id of idMatches) {
                                            let status = "Unknown";
                                            if (text.includes('1/1') || text.includes('AVAILABLE') || text.includes('Verfügbar')) {
                                                status = "Available";
                                            } else if (text.includes('0/1') || text.includes('OCCUPIED') || text.includes('Besetzt')) {
                                                status = "Occupied";
                                            }

                                            let type = "Unknown";
                                            if (text.includes('Typ 2') || text.includes('Typ2')) type = "Type 2";
                                            else if (text.includes('CCS')) type = "CCS";

                                            results.push({ id, status, type });
                                        }
                                    }
                                }
                                if (node.shadowRoot) walk(node.shadowRoot);
                                for (const child of node.childNodes || []) {
                                    if (child.nodeType === 1) walk(child);
                                }
                            }
                            walk(document.body);
                            return results;
                        }
                    """)

                    if connectors:
                        unique = {}
                        for c in connectors:
                            cid = c['id']
                            # Keep the one with a known status if multiple entries exist
                            # And avoid shorter partial IDs if we have longer ones (though regex should handle it)
                            if cid not in unique or (unique[cid]['status'] == 'Unknown' and c['status'] != 'Unknown'):
                                unique[cid] = c
                        found_connectors = list(unique.values())
                        if found_connectors:
                            # Verify if we found the expected IDs
                            if any("DE*LVP*E21065*001" in c['id'] for c in found_connectors):
                                break

                    await page.wait_for_timeout(5000)

                if found_connectors:
                    self.status_data["connectors"] = found_connectors
                    self.status_data["status"] = "OK"
                    self.status_data["error"] = None
                    logger.info(f"Success: {len(found_connectors)} connectors found.")
                else:
                    self.status_data["error"] = "Data not found in DOM."
                    await page.screenshot(path="scrape_fail.png")

            except Exception as e:
                logger.error(f"Scraper error: {e}")
                self.status_data["error"] = str(e)
            finally:
                self.status_data["last_updated"] = datetime.now().isoformat()
                await browser_context.close()

        return self.status_data

if __name__ == "__main__":
    scraper = ChargerScraper("https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583")
    print(json.dumps(asyncio.run(scraper.scrape()), indent=2))
