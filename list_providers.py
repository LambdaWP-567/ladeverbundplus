
import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(5000)

        providers = await page.evaluate("""
            () => {
                const results = [];
                const items = document.querySelectorAll('ion-item');
                for (const item of items) {
                    results.push({
                        text: item.innerText.trim(),
                        html: item.outerHTML
                    });
                }
                return results;
            }
        """)

        print(json.dumps(providers, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
