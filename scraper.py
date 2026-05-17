import asyncio
from playwright.async_api import async_playwright
import json
import logging
from datetime import datetime
import os
import re
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChargerScraper:
    def __init__(self, url, provider_name="Erlanger Stadtwerke", verbose=False):
        self.url = url
        self.provider_name = provider_name
        self.verbose = verbose
        self.status_data = {"status": "Unknown", "connectors": [], "last_updated": None, "error": "Not started"}
        self.user_data_dir = f"/tmp/playwright_session_{os.getpid()}_{datetime.now().microsecond}"

    def _log(self, msg, level=logging.INFO):
        logger.log(level, msg)

    async def scrape(self):
        self._log(f"--- STARTING SCRAPE (VERSION 1.3.0) ---")
        async with async_playwright() as p:
            browser_context = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 1200},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await browser_context.new_page()

            if self.verbose:
                page.on("console", lambda msg: self._log(f"BROWSER: {msg.text}", logging.DEBUG))

            try:
                # 1. Navigation with retry
                self._log(f"Navigating to root to establish session...")
                await page.goto("https://ladeverbundplus.chargecloud.de/", wait_until="load")
                await asyncio.sleep(10)

                for cycle in range(1, 15):
                    curr_url = page.url
                    self._log(f"Cycle {cycle} | URL: {curr_url}")

                    # A. Handle Provider Selection
                    if "/settings" in curr_url or await page.evaluate("() => document.body.innerText.includes('Anbieter wählen')"):
                        self._log(f"Selecting Provider: {self.provider_name}")
                        await page.get_by_text(self.provider_name).first.click()
                        await asyncio.sleep(10)
                        self._log(f"Navigating to station details...")
                        await page.goto(self.url, wait_until="load")
                        await asyncio.sleep(10)
                        continue

                    # B. Cleanup Overlays & Modals
                    await page.evaluate("""() => {
                        const words = ["VERSTANDEN", "OK", "CLOSE", "AGREE"];
                        document.querySelectorAll('button, ion-button, span, div').forEach(b => {
                            if (words.includes((b.innerText || "").trim().toUpperCase())) b.click();
                        });
                        const sel = 'ion-loading, ion-backdrop, .loading-wrapper, ion-spinner, .backdrop-no-tappable, ion-modal';
                        document.querySelectorAll(sel).forEach(el => el.remove());
                        document.body.classList.remove('modal-open');
                    }""")

                    # C. Unified Extraction Attempt
                    # This logic finds IDs and Availability Markers by scanning all text nodes
                    # and associating them by finding common parents or grouping by proximity.
                    extraction = await page.evaluate("""() => {
                        const nodes = [];
                        const idRegex = /DE\\*LVP\\*[A-Z0-9\\*]+/g;

                        function walk(root) {
                            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
                            let node;
                            while (node = walker.nextNode()) {
                                const t = node.textContent.trim();
                                if (t.includes('DE*LVP') || t.includes('1/1') || t.includes('0/1') || t.includes('1 / 1') || t.includes('0 / 1')) {
                                    nodes.push({
                                        text: t,
                                        // We find a significant ancestor to help group ID with its status
                                        ancestor: node.parentElement.closest('ion-item, .item-block, div[fittext]') || node.parentElement
                                    });
                                }
                            }
                            Array.from(root.querySelectorAll('*')).forEach(el => {
                                if (el.shadowRoot) walk(el.shadowRoot);
                            });
                        }
                        walk(document.body);

                        // Grouping logic: find markers and associate with nearest ID
                        const results = [];
                        const seenIds = new Set();

                        // Simple association: we found that they often appear in sequence in the DOM scan
                        let currentId = null;
                        for (let i = 0; i < nodes.length; i++) {
                            const n = nodes[i];
                            const idMatch = n.text.match(idRegex);
                            if (idMatch) {
                                currentId = idMatch[0].trim().replace(/[^A-Z0-9\\*]$/, '');
                                // Look forward for status
                                let status = "Unknown";
                                for (let j = i + 1; j < Math.min(i + 5, nodes.length); j++) {
                                    const next = nodes[j];
                                    if (next.text.includes('1 / 1') || next.text.includes('1/1')) { status = "Available"; break; }
                                    if (next.text.includes('0 / 1') || next.text.includes('0/1')) { status = "Occupied"; break; }
                                    if (next.text.includes('DE*LVP')) break; // Hit next connector
                                }
                                if (!seenIds.has(currentId)) {
                                    results.push({ id: currentId, status });
                                    seenIds.add(currentId);
                                }
                            }
                        }
                        return results;
                    }""")

                    if extraction and any(c['status'] != 'Unknown' for c in extraction):
                        self.status_data["connectors"] = sorted(extraction, key=lambda x: x['id'])
                        self.status_data["status"] = "OK"
                        self.status_data["error"] = None
                        self._log(f"Extraction successful! Found {len(extraction)} connectors.")
                        return self.status_data

                    if cycle % 3 == 0:
                        self._log("Hydration stuck? Reloading station page...")
                        await page.goto(self.url, wait_until="load")
                        await asyncio.sleep(15)
                    else:
                        await asyncio.sleep(8)

                self.status_data["error"] = "Data not found after 15 cycles."
                self._log("Failed to find data markers.", logging.ERROR)

            except Exception as e:
                self._log(f"Scraper error: {e}", logging.ERROR)
                self.status_data["error"] = str(e)
            finally:
                self.status_data["last_updated"] = datetime.now().isoformat()
                await browser_context.close()
                if os.path.exists(self.user_data_dir):
                    shutil.rmtree(self.user_data_dir, ignore_errors=True)

        return self.status_data

if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
    scraper = ChargerScraper(u, verbose=True)
    print(json.dumps(asyncio.run(scraper.scrape()), indent=2))
