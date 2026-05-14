
import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'
        print(f"Loading {url}...")
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(10000)

        # Capture all text on page
        text_content = await page.evaluate("() => document.body.innerText")
        print("--- PAGE TEXT START ---")
        print(text_content[:2000])
        print("--- PAGE TEXT END ---")

        # Look for ion-item labels
        labels = await page.evaluate("""
            () => {
                const results = [];
                const items = document.querySelectorAll('ion-label');
                for (const item of items) {
                    results.push(item.innerText.trim());
                }
                return results;
            }
        """)
        print(f"Found {len(labels)} ion-labels: {labels[:20]}")

        await page.screenshot(path='structure_check.png')
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
