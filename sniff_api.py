
import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        async def handle_response(response):
            try:
                # Log all non-static responses
                if response.status == 200 and not any(ext in response.url for ext in [".js", ".css", ".png", ".jpg", ".woff", ".svg"]):
                    text = await response.text()
                    if "3411583" in text or "LVP" in text or "Verfügbar" in text or "Besetzt" in text:
                         print(f"\n--- MATCH FOUND ---")
                         print(f"URL: {response.url}")
                         print(f"Type: {response.request.resource_type}")
                         print(f"Content Snippet: {text[:500]}...")
            except:
                pass

        page.on("response", handle_response)

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'
        print(f"Loading {url}...")
        await page.goto(url, wait_until="load")

        print("Waiting 15s for initial load and possible provider selection...")
        await page.wait_for_timeout(15000)

        # Check for provider selection
        has_provider = await page.query_selector('ion-title:has-text("PROVIDER")')
        if has_provider:
            print("Selecting Erlanger Stadtwerke...")
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
            await page.wait_for_timeout(10000)
            print("Reloading...")
            await page.goto(url, wait_until="load")

        print("Waiting 30s for data...")
        await page.wait_for_timeout(30000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
