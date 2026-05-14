
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
        await page.wait_for_timeout(10000)

        print("Initial titles:")
        titles = await page.query_selector_all('ion-title')
        for t in titles:
            print(f"Title: {await t.inner_text()}")

        # Search for Erlanger Stadtwerke in all elements
        found = await page.evaluate("""
            () => {
                const results = [];
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.innerText && el.innerText.includes('Erlanger Stadtwerke')) {
                        results.push({
                            tag: el.tagName,
                            classes: el.className,
                            text: el.innerText.substring(0, 50)
                        });
                    }
                }
                return results;
            }
        """)
        print(f"Found 'Erlanger Stadtwerke' in {len(found)} elements.")
        # print(json.dumps(found[:10], indent=2))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
