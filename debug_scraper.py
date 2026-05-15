import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        url = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"

        logger.info(f"Loading {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)

        # Second load
        logger.info("Second load...")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)

        content = await page.content()
        with open("page_debug.html", "w") as f:
            f.write(content)

        # Try to find the provider button if it's there
        try:
            # Look for "Erlanger Stadtwerke"
            await page.click("text=Erlanger Stadtwerke", timeout=5000)
            logger.info("Clicked provider")
            await asyncio.sleep(2)
        except:
            logger.info("Provider not found/needed")

        content_after = await page.content()
        with open("page_debug_after.html", "w") as f:
            f.write(content_after)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
