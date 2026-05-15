import asyncio
from playwright.async_api import async_playwright

async def dump():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        url = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
        await page.goto(url, wait_until="load")
        await asyncio.sleep(5)
        await page.goto(url, wait_until="load")
        await asyncio.sleep(10)

        texts = await page.evaluate("""
            () => {
                const results = [];
                function search(root) {
                    Array.from(root.querySelectorAll('ion-item, ion-card, .item, .item-inner')).forEach(el => {
                        results.push(el.innerText);
                    });
                    Array.from(root.querySelectorAll('*')).forEach(child => {
                        if (child.shadowRoot) search(child.shadowRoot);
                    });
                }
                search(document.body);
                return results;
            }
        """)
        for t in texts:
            print("--- ELEMENT ---")
            print(t)
        await browser.close()

asyncio.run(dump())
