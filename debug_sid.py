import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3290015"
        await page.goto(url, wait_until="load")
        await asyncio.sleep(10)
        await page.goto(url, wait_until="load")
        await asyncio.sleep(10)

        # Get all text content from all elements that might contain status
        content = await page.evaluate("""
            () => {
                const results = [];
                function search(root) {
                    const els = Array.from(root.querySelectorAll('*'));
                    els.forEach(el => {
                        if (el.innerText && el.innerText.includes('DE*LVP*E22062')) {
                            results.push(el.innerText);
                        }
                    });
                    els.forEach(child => { if(child.shadowRoot) search(child.shadowRoot); });
                }
                search(document.body);
                return results;
            }
        """)
        for i, text in enumerate(content):
             print(f"--- BLOCK {i} ---")
             print(text)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
