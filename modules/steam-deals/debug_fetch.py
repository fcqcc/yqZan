"""Debug fetch_more_deals"""
import asyncio, httpx
from app.steam_fetcher import fetch_more_deals

async def debug():
    async with httpx.AsyncClient(timeout=30) as client:
        deals = await fetch_more_deals(client, limit=10)
        print(f'\nfetch_more_deals returned: {len(deals)} deals')
        for d in deals:
            print(f'  {d["name"][:25]:25s}  -{d["discount_percent"]}%  ¥{d["final_price"]:.0f}')

asyncio.run(debug())
