import asyncio
import httpx

async def test():
    key = "d9qabphr01qvh74e4pi0d9qabphr01qvh74e4pig"
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(f"https://finnhub.io/api/v1/news?category=general&token={key}")
        news = r.json()
        if isinstance(news, list) and news:
            print(f"Finnhub OK - {len(news)} articles")
            print(f"First: {news[0]['headline'][:80]}")
        else:
            print(f"Finnhub response: {news}")

asyncio.run(test())
