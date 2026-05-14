
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
        user_data_dir = "/tmp/playwright_final_test"
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=True)
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'

        logger.info("Loading page...")
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(5000)

        # Check for provider selection
        has_provider = await page.query_selector('ion-title:has-text("PROVIDER")')
        if has_provider:
            logger.info("Selecting Provider: Erlanger Stadtwerke...")
            # Click the exact ion-item
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
            await page.wait_for_timeout(5000)

        # Reloading
        logger.info("Reloading to get station details...")
        await page.goto(url, wait_until="load")

        logger.info("Waiting 30s for station data...")
        await page.wait_for_timeout(30000)

        # Check title
        title = await page.evaluate("() => document.querySelector('ion-title').innerText")
        logger.info(f"Page Title: {title}")

        # Check all text for keywords
        content = await page.evaluate("() => document.body.innerText")
        logger.info(f"Content length: {len(content)}")

        if "Buckenhofer" in content:
            logger.info("FOUND 'Buckenhofer' in content!")
        if "DE*LVP" in content:
            logger.info("FOUND 'DE*LVP' in content!")
        if "1/1" in content:
            logger.info("FOUND '1/1' in content!")

        await page.screenshot(path='final_test.png')
        with open("final_test.html", "w") as f:
            f.write(await page.content())

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
