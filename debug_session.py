
import asyncio
from playwright.async_api import async_playwright
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a persistent context to simulate the user's browser
        user_data_dir = "/tmp/playwright_debug_session"
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=True)
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'

        logger.info("Step 1: 1st Load...")
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(5000)

        logger.info("Step 2: Selecting Provider...")
        clicked = await page.evaluate("""
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
        logger.info(f"Provider clicked: {clicked}")
        await page.wait_for_timeout(5000)

        logger.info("Step 3: 2nd Load (same session)...")
        await page.goto(url, wait_until="load")

        logger.info("Step 4: Waiting for data (up to 60s)...")
        for i in range(1, 13):
            logger.info(f"Waiting attempt {i}/12...")
            content = await page.content()
            if "Buckenhofer" in content or "DE*LVP" in content:
                logger.info("SUCCESS: Station details found in page content!")
                break
            await page.wait_for_timeout(5000)

        await page.screenshot(path='debug_session.png')
        with open("debug_session.html", "w") as f:
            f.write(await page.content())

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
