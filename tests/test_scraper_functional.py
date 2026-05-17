import pytest
from scraper import ChargerScraper

@pytest.mark.asyncio
async def test_scraper_logic():
    scraper = ChargerScraper(verbose=False)
    # We test the specific station provided by user
    url = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/3411583"
    try:
        data = await scraper.scrape_station(url, provider_name="Erlanger Stadtwerke")
        assert data is not None
        assert len(data) > 0
        for conn in data:
            assert "id" in conn
            assert "status" in conn
            assert conn["status"] in ["Available", "Occupied", "Unknown"]
    finally:
        await scraper.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_scraper_logic())
