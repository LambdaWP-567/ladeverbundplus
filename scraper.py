
import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime

class ChargerScraper:
    def __init__(self, url, provider_name="Erlanger Stadtwerke"):
        self.url = url
        self.provider_name = provider_name
        self.status_data = {
            "status": "Unknown",
            "connectors": [],
            "last_updated": None,
            "error": None
        }

    async def scrape(self):
        async with async_playwright() as p:
            # Persistent context helps with maintaining "session" or provider choice if the site uses cookies/localStorage
            user_data_dir = "/tmp/playwright_user_data_v15"
            browser_context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=True,
                viewport={'width': 1280, 'height': 800}
            )
            page = await browser_context.new_page()

            try:
                print(f"[{datetime.now()}] Loading {self.url}...")
                await page.goto(self.url, wait_until="load", timeout=60000)

                # Wait for provider selection if it appears
                try:
                    await page.wait_for_selector('ion-title:has-text("PROVIDER")', timeout=10000)
                    print(f"[{datetime.now()}] Provider selection detected. Selecting {self.provider_name}...")
                    await page.evaluate(f"""
                        (providerName) => {{
                            const items = document.querySelectorAll('ion-item');
                            for (const item of items) {{
                                if (item.innerText.includes(providerName)) {{
                                    item.click();
                                    return true;
                                }}
                            }}
                            return false;
                        }}
                    """, self.provider_name)
                    await page.wait_for_timeout(5000)
                    # Reload as suggested by user for 2nd load behavior
                    await page.goto(self.url, wait_until="load", timeout=60000)
                except:
                    print(f"[{datetime.now()}] Provider selection not seen or already selected.")

                # Wait for actual content
                print(f"[{datetime.now()}] Waiting for connector data...")
                # We search for ion-items that contain status words
                found_connectors = []
                for _ in range(12): # 60 seconds
                    items = await page.query_selector_all('ion-item')
                    for item in items:
                        text = await item.inner_text()
                        if any(s in text for s in ["Verfügbar", "Besetzt", "Available", "Occupied"]):
                            status = "Available" if ("Verfügbar" in text or "Available" in text) else "Occupied"
                            ctype = "Type 2" if "Typ 2" in text else "CCS" if "CCS" in text else "Unknown"
                            if not any(c['raw'] == text.strip().replace('\n', ' ') for c in found_connectors):
                                found_connectors.append({
                                    "type": ctype,
                                    "status": status,
                                    "raw": text.strip().replace('\n', ' ')
                                })
                    if found_connectors:
                        break
                    await page.wait_for_timeout(5000)

                if found_connectors:
                    self.status_data["status"] = "OK"
                    self.status_data["connectors"] = found_connectors
                    self.status_data["error"] = None
                else:
                    self.status_data["status"] = "Unknown"
                    self.status_data["error"] = "Could not find connector status on page."
                    # Debug save
                    await page.screenshot(path="latest_fail.png")

            except Exception as e:
                self.status_data["status"] = "Unknown"
                self.status_data["error"] = str(e)
            finally:
                self.status_data["last_updated"] = datetime.now().isoformat()
                await browser_context.close()

        return self.status_data

if __name__ == "__main__":
    scraper = ChargerScraper('https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583')
    result = asyncio.run(scraper.scrape())
    print(json.dumps(result, indent=2))
