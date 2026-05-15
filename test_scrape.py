import asyncio
from scraper import ChargerScraper
import sys

async def main():
    url = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
    scraper = ChargerScraper(url)
    print(f"Starting test scrape for {url}...")
    result = await scraper.scrape()

    if result["status"] == "OK" and len(result["connectors"]) > 0:
        print("✅ TEST PASSED: Successfully retrieved data.")
        for c in result["connectors"]:
            print(f"  - {c['id']}: {c['status']}")
        sys.exit(0)
    else:
        print("❌ TEST FAILED: Could not retrieve data.")
        print(f"  Error: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
