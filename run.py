import aiohttp
import asyncio

API_KEY = ""
LATITUDE = -30.24
LONGITUDE = -70.336
ELEVATION = 2925
TIMEZONE = "America/Santiago"
SITE_URL = "https://my.meteoblue.com/packages/trend-1h"
FORMAT = "json"

async def main():
    params = {"lat": LATITUDE, "lon": LONGITUDE, "apikey": API_KEY}
    async with aiohttp.ClientSession("http://my.meteoblue.com", raise_for_status=True) as session:
        async with session.get("/packages/trendpro-1h_trendpro-day", params=params) as resp:
            with open("forecast.json", 'wb') as fd:
                async for chunk in resp.content.iter_chunked(1024):
                    fd.write(chunk)

asyncio.run(main())