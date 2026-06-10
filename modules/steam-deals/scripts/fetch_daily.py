#!/usr/bin/env python3
"""Steam 折扣每日抓取 + 保存到数据库"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.steam_fetcher import fetch_all_deals
from app.database import init_db, save_daily_deals

async def main():
    print("=" * 50)
    print("Steam 折扣每日抓取器")
    print("=" * 50)
    
    init_db()
    deals = await fetch_all_deals(include_more=True)
    save_daily_deals(deals)
    
    total = len(deals)
    bargains = sum(1 for d in deals if d.get("final_price", 0) <= 10)
    top = sorted([d for d in deals if d.get("worth_index", 0) > 0],
                 key=lambda x: x["worth_index"], reverse=True)[:5]
    
    print(f"\n✅ 完成！共 {total} 条折扣")
    print(f"🥬 白菜价(≤¥10): {bargains} 款")
    print(f"\n🏆 今日最佳:")
    for d in top:
        print(f"   {d['name']}  -{d['discount_percent']}%  ¥{d['final_price']:.0f}  指数{d['worth_index']:.0f}")

asyncio.run(main())
