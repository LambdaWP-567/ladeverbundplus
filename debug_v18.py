
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
        user_data_dir = "/tmp/playwright_debug_session_v2"
        context = await p.chromium.launch_persistent_context(user_data_dir, headless=True)
        page = await context.new_page()

        url = 'https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583'

        logger.info("1st Load...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000)

        # Check for provider selection
        has_provider = await page.query_selector('ion-title:has-text("PROVIDER")')
        if has_provider:
            logger.info("Provider Selection Screen detected.")
            # List providers
            providers = await page.evaluate("() => Array.from(document.querySelectorAll('ion-item')).map(el => el.innerText)")
            logger.info(f"Available providers: {providers[:5]}")

            # Click Erlanger Stadtwerke
            logger.info("Clicking Erlanger Stadtwerke...")
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

            # Check if still on provider screen
            has_provider_still = await page.query_selector('ion-title:has-text("PROVIDER")')
            logger.info(f"Still on provider screen? {has_provider_still is not None}")

            # If so, maybe we need to reload or it's stuck
            if has_provider_still:
                logger.info("STUCK on provider screen. Trying to reload same URL...")
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(10000)

        # Capture status
        await page.screenshot(path='debug_v18.png')
        with open("debug_v18.html", "w") as f:
            f.write(await page.content())

        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
