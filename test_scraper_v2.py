
import asyncio
from scraper import ChargerScraper
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_scraper():
    print("Testing Scraper...")
    scraper = ChargerScraper('https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583')
    result = await scraper.scrape()

    print("\nScraper Result:")
    print(json.dumps(result, indent=2))

    if result["status"] == "OK" and len(result["connectors"]) > 0:
        print("\nSUCCESS: Found connectors!")
        for c in result["connectors"]:
            print(f"ID: {c['id']}, Status: {c['status']}, Type: {c['type']}")
    else:
        print("\nFAILURE: Could not find connectors.")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
