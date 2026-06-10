"""
Steam 好价追踪 — FastAPI 主应用
"""
import asyncio
import os
import sys
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 确保模块可导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import (
    init_db, get_today_deals, get_today_top_deals,
    get_bargain_deals, search_deals, get_genres,
)
from app.game_names import GAME_NAMES

app = FastAPI(title="Steam 好价追踪", version="1.0.0")

# 挂载静态文件
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


def _add_cn_names(deals: list) -> list:
    """为返回数据补充中文名"""
    for d in deals:
        if not d.get("name_cn") and d.get("name") in GAME_NAMES:
            d["name_cn"] = GAME_NAMES[d["name"]]
    return deals


@app.get("/api/today")
async def today_deals(fetched_date: str = None):
    """获取当天所有折扣"""
    deals = get_today_deals(fetched_date)
    return {
        "count": len(deals),
        "fetched_date": fetched_date or date.today().isoformat(),
        "deals": deals,
    }


@app.get("/api/top")
async def top_deals(limit: int = Query(10, ge=1, le=50), fetched_date: str = None):
    """获取当日精选 Top N"""
    deals = get_today_top_deals(limit, fetched_date)
    return {
        "count": len(deals),
        "fetched_date": fetched_date or date.today().isoformat(),
        "deals": deals,
    }


@app.get("/api/bargains")
async def bargain_deals(max_price: int = Query(20, ge=1, le=50), fetched_date: str = None):
    """白菜价专区（低价游戏）"""
    deals = get_bargain_deals(fetched_date, max_price)
    return {
        "count": len(deals),
        "fetched_date": fetched_date or date.today().isoformat(),
        "deals": deals,
    }


@app.get("/api/search")
async def search(
    q: str = Query("", description="搜索关键词"),
    min_discount: int = Query(0, ge=0, le=100),
    max_price: float = Query(None, ge=0),
    genre: str = Query(None),
    sort_by: str = Query("worth", pattern="^(worth|discount|price_asc|price_desc|rating|name)$"),
    limit: int = Query(50, ge=1, le=200),
    fetched_date: str = None,
):
    """搜索+筛选折扣游戏"""
    deals = search_deals(
        query=q, fetched_date=fetched_date,
        min_discount=min_discount, max_price=max_price,
        genre=genre, sort_by=sort_by, limit=limit
    )
    return {
        "count": len(deals),
        "fetched_date": fetched_date or date.today().isoformat(),
        "query": q,
        "deals": deals,
    }


@app.get("/api/genres")
async def genres(fetched_date: str = None):
    """获取当前可筛选的游戏类型"""
    return {
        "genres": get_genres(fetched_date),
        "fetched_date": fetched_date or date.today().isoformat(),
    }


@app.get("/api/stats")
async def stats(fetched_date: str = None):
    """当日统计数据"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    deals = get_today_deals(fetched_date)
    total = len(deals)
    bargains = sum(1 for d in deals if d.get("final_price", 999) <= 10)
    big_sales = sum(1 for d in deals if d.get("discount_percent", 0) >= 70)
    top_game = deals[0] if deals else None
    avg_discount = sum(d.get("discount_percent", 0) or 0 for d in deals) / max(total, 1)
    return {
        "fetched_date": fetched_date,
        "total_deals": total,
        "bargain_count": bargains,
        "big_sale_count": big_sales,
        "avg_discount_percent": round(avg_discount, 1),
        "top_game": top_game,
    }


@app.get("/api/export/wechat")
async def export_wechat_article(fetched_date: str = None):
    """生成公众号图文素材内容"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    top = get_today_top_deals(10, fetched_date)
    bargains = get_bargain_deals(fetched_date, 10)
    stats_data = await stats(fetched_date)
    deals = get_today_deals(fetched_date)

    # 按类型分组
    from collections import Counter
    genre_count = Counter()
    for d in deals:
        for g in (d.get("genre", "") or "").split(","):
            g = g.strip()
            if g:
                genre_count[g] += 1

    top_types = [{"genre": g, "count": c} for g, c in genre_count.most_common(8)]

    return JSONResponse({
        "title": f"Steam 好价日报 | {fetched_date}",
        "date": fetched_date,
        "summary": f"今日共 {stats_data['total_deals']} 款游戏打折，{stats_data['bargain_count']} 款白菜价，{stats_data['big_sale_count']} 款超低价(≥70% off)",
        "content": {
            "top_10": [
                {
                    "name": d["name"],
                    "discount": f"-{d['discount_percent']}%",
                    "old_price": f"¥{d['original_price']:.0f}" if d["original_price"] else "?",
                    "new_price": f"¥{d['final_price']:.0f}",
                    "rating": f"{d['steam_rating_percent']}%好评" if d["steam_rating_percent"] else "暂无评分",
                    "worth_index": d.get("worth_index", 0),
                    "genre": d.get("genre", ""),
                    "image": d.get("header_image", ""),
                    "is_historic": bool(d.get("is_historic_low")),
                }
                for d in top
            ],
            "bargains": [
                {
                    "name": d["name"],
                    "price": f"¥{d['final_price']:.0f}",
                    "discount": f"-{d['discount_percent']}%",
                }
                for d in bargains[:10]
            ],
            "genre_overview": top_types,
        }
    })


@app.get("/", response_class=HTMLResponse)
async def index():
    """PWA 前端页面"""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Steam 好价追踪器</h1><p>前端页面正在构建...</p>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=5050, reload=True)
