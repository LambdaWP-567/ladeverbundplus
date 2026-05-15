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
    def __init__(self, url, provider_name="Erlanger Stadtwerke", verbose=False):
        self.url = url
        self.provider_name = provider_name
        self.verbose = verbose
        self.status_data = {"status": "Unknown", "connectors": [], "last_updated": None, "error": "Not started"}
        self.user_data_dir = "/tmp/playwright_persistent_session"
        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def _log(self, msg, level=logging.INFO):
        logger.log(level, msg)

    async def scrape(self):
        async with async_playwright() as p:
            browser_context = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await browser_context.new_page()

            if self.verbose:
                page.on("console", lambda msg: logger.debug(f"BROWSER CONSOLE: {msg.text}"))
                page.on("requestfailed", lambda req: logger.debug(f"REQUEST FAILED: {req.url} - {req.failure}"))

            try:
                self._log(f"Navigating to {self.url}")
                await page.goto(self.url, wait_until="load", timeout=60000)
                await asyncio.sleep(10)

                # Double load trick
                self._log("Performing double-load for SPA hydration...")
                await page.goto(self.url, wait_until="load", timeout=60000)
                await asyncio.sleep(15)

                # Check for redirects or blocking screens
                current_url = page.url
                self._log(f"Current URL after load: {current_url}")

                if "/home" in current_url or "/search" in current_url:
                    self._log("Detected redirect to home/search. Re-navigating to details...")
                    await page.goto(self.url, wait_until="load")
                    await asyncio.sleep(15)

                # Dismiss overlays
                for i in range(3):
                    self._log(f"Checking for overlays (Attempt {i+1})...")
                    overlay_clicked = await page.evaluate("""
                        () => {
                            const words = ["Verstanden", "OK", "Zustimmen", "Accept", "Schließen", "Close", "Annehmen"];
                            let found = null;
                            function search(root) {
                                if (found) return;
                                const els = Array.from(root.querySelectorAll('button, ion-button, .button, span, div[role="button"]'));
                                for (const el of els) {
                                    if (words.some(w => el.innerText && el.innerText.trim().includes(w))) {
                                        const style = window.getComputedStyle(el);
                                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                                            el.click();
                                            found = el.innerText;
                                            return;
                                        }
                                    }
                                }
                                Array.from(root.querySelectorAll('*')).forEach(child => {
                                    if (child.shadowRoot) search(child.shadowRoot);
                                });
                            }
                            search(document.body);
                            return found;
                        }
                    """)
                    if overlay_clicked:
                        self._log(f"Clicked overlay button: {overlay_clicked}")
                        await asyncio.sleep(5)
                    else:
                        break

                # Extraction loop
                found_connectors = []
                for attempt in range(1, 10):
                    self._log(f"Extraction Attempt {attempt}...")

                    if self.verbose:
                        await page.screenshot(path=f"debug_attempt_{attempt}.png")

                    connectors = await page.evaluate("""
                        () => {
                            const results = [];
                            const idRegex = /DE\\*LVP\\*[A-Z0-9\\*]+/g;
                            const seenIds = new Set();

                            function search(root) {
                                // Depth-first traversal into shadows
                                const els = Array.from(root.querySelectorAll('*'));
                                for (const el of els) {
                                    if (el.shadowRoot) search(el.shadowRoot);
                                }

                                const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
                                let node;
                                while (node = walker.nextNode()) {
                                    const text = node.textContent;
                                    const matches = text.match(idRegex);
                                    if (matches) {
                                        for (let id of matches) {
                                            id = id.trim().replace(/[^A-Z0-9\\*]$/, '');
                                            if (seenIds.has(id) || id.length < 10) continue;

                                            let contextText = "";
                                            let curr = node.parentElement;
                                            // Broad context search
                                            for (let i = 0; i < 30; i++) {
                                                if (!curr) break;
                                                contextText += " " + (curr.innerText || "");
                                                curr = curr.parentElement;
                                            }

                                            let status = "Unknown";
                                            const availTerms = ['1/1', '1 / 1', 'Verfügbar', 'AVAILABLE', 'FREE', 'FREI'];
                                            const busyTerms = ['0/1', '0 / 1', 'Besetzt', 'OCCUPIED', 'BELEGT', 'In Use', 'In Gebrauch'];

                                            if (availTerms.some(t => contextText.includes(t))) {
                                                status = "Available";
                                            } else if (busyTerms.some(t => contextText.includes(t))) {
                                                status = "Occupied";
                                            }

                                            results.push({ id, status, context: contextText.length });
                                            seenIds.add(id);
                                        }
                                    }
                                }
                            }
                            search(document.body);
                            return results;
                        }
                    """)

                    if connectors:
                        valid = [c for c in connectors if len(c['id'].split('*')) >= 4]
                        if valid:
                            # Prioritize connectors with known status
                            found_connectors = valid
                            if any(c['status'] != 'Unknown' for c in valid):
                                self._log(f"Found {len(valid)} connectors with status.")
                                break
                            else:
                                self._log(f"Found {len(valid)} IDs but status is still Unknown. Retrying...")

                    await asyncio.sleep(5)

                if found_connectors:
                    self.status_data["connectors"] = sorted(found_connectors, key=lambda x: x['id'])
                    self.status_data["status"] = "OK"
                    self.status_data["error"] = None
                    self._log(f"Scrape successful: {len(found_connectors)} connectors found.")
                else:
                    self.status_data["error"] = "Data not found or incomplete."
                    self._log("Scrape failed: Data not found.", logging.WARNING)
                    await page.screenshot(path="scrape_failure_final.png")

            except Exception as e:
                self._log(f"Scraper error: {e}", logging.ERROR)
                self.status_data["error"] = str(e)
            finally:
                self.status_data["last_updated"] = datetime.now().isoformat()
                await browser_context.close()

        return self.status_data

if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
    scraper = ChargerScraper(u, verbose=True)
    print(json.dumps(asyncio.run(scraper.scrape()), indent=2))
