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
                await asyncio.sleep(10)

                # Second load
                await page.goto(self.url, wait_until="load", timeout=60000)
                await asyncio.sleep(10)

                # Extraction
                found_connectors = []
                for attempt in range(1, 6):
                    logger.info(f"Extraction Attempt {attempt}...")

                    connectors = await page.evaluate("""
                        () => {
                            const results = [];
                            const idRegex = /DE\\*LVP\\*[A-Z0-9\\*]+/g;
                            const seenIds = new Set();

                            function search(root) {
                                // Try finding containers first (ion-item, ion-card)
                                const containers = Array.from(root.querySelectorAll('ion-item, ion-card, .item-inner, .list-item'));
                                for (const container of containers) {
                                    const text = container.innerText || "";
                                    const matches = text.match(idRegex);
                                    if (matches) {
                                        for (let id of matches) {
                                            id = id.trim().replace(/[^A-Z0-9\\*]$/, '');
                                            if (seenIds.has(id)) continue;

                                            let status = "Unknown";
                                            if (text.includes('1/1') || text.includes('Verfügbar') || text.includes('AVAILABLE')) {
                                                status = "Available";
                                            } else if (text.includes('0/1') || text.includes('Besetzt') || text.includes('OCCUPIED') || text.includes('Belegt')) {
                                                status = "Occupied";
                                            }
                                            results.push({ id, status });
                                            seenIds.add(id);
                                        }
                                    }
                                }

                                // Fallback to text nodes
                                if (results.length === 0) {
                                    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
                                    let node;
                                    while (node = walker.nextNode()) {
                                        const text = node.textContent;
                                        const matches = text.match(idRegex);
                                        if (matches) {
                                            for (let id of matches) {
                                                id = id.trim().replace(/[^A-Z0-9\\*]$/, '');
                                                if (seenIds.has(id)) continue;

                                                let contextText = "";
                                                let curr = node.parentElement;
                                                for (let i = 0; i < 10; i++) {
                                                    if (!curr) break;
                                                    contextText += " " + curr.innerText;
                                                    curr = curr.parentElement;
                                                }

                                                let status = "Unknown";
                                                if (contextText.includes('1/1') || contextText.includes('Verfügbar') || contextText.includes('AVAILABLE')) {
                                                    status = "Available";
                                                } else if (contextText.includes('0/1') || contextText.includes('Besetzt') || contextText.includes('OCCUPIED') || contextText.includes('Belegt')) {
                                                    status = "Occupied";
                                                }
                                                results.push({ id, status });
                                                seenIds.add(id);
                                            }
                                        }
                                    }
                                }

                                Array.from(root.querySelectorAll('*')).forEach(child => {
                                    if (child.shadowRoot) search(child.shadowRoot);
                                });
                            }
                            search(document.body);
                            return results;
                        }
                    """)

                    if connectors:
                        cleaned = [c for c in connectors if len(c['id'].split('*')) >= 4]
                        if cleaned:
                            found_connectors = cleaned
                            if any(c['status'] != 'Unknown' for c in cleaned):
                                break

                    await asyncio.sleep(5)

                if found_connectors:
                    self.status_data["connectors"] = sorted(found_connectors, key=lambda x: x['id'])
                    self.status_data["status"] = "OK"
                    self.status_data["error"] = None
                    logger.info(f"Success: {self.status_data['connectors']}")
                else:
                    self.status_data["error"] = "Data not found or incomplete."
                    await page.screenshot(path="debug_extraction.png")

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
