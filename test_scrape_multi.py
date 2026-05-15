import asyncio
from scraper import ChargerScraper

async def test():
    urls = [
        "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583",
        "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3290015"
    ]
    for url in urls:
        print(f"Testing {url}...")
        scraper = ChargerScraper(url)
        res = await scraper.scrape()
        print(f"Result for {url}: {res['status']}")
        if res['status'] == 'OK':
            for c in res['connectors']:
                print(f"  {c['id']}: {c['status']}")
        else:
            print(f"  Error: {res.get('error')}")

if __name__ == "__main__":
    asyncio.run(test())
