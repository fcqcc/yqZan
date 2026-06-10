"""
Steam API 数据抓取模块
从多个 Steam API 端点获取折扣数据
"""
import asyncio
import httpx
import re
import json
from datetime import date
from typing import Optional

STEAM_STORE = "https://store.steampowered.com"
API_FEATURED = f"{STEAM_STORE}/api/featuredcategories"
API_APPDETAILS = f"{STEAM_STORE}/api/appdetails"
API_SEARCH = f"{STEAM_STORE}/api/storesearch"
CC = "cn"
LANG = "zh-cn"

# 游戏类型关键词映射（Steam 返回的标签 → 我们用的类型）
GENRE_KEYWORDS = {
    "动作": "动作", "ACT": "动作", "Action": "动作",
    "冒险": "冒险", "Adventure": "冒险",
    "角色扮演": "RPG", "RPG": "RPG", "Role Playing": "RPG",
    "模拟": "模拟", "Simulation": "模拟", "模拟经营": "模拟",
    "策略": "策略", "Strategy": "策略",
    "体育": "体育", "Sports": "体育",
    "竞速": "竞速", "Racing": "竞速",
    "休闲": "休闲", "Casual": "休闲",
    "独立": "独立", "Indie": "独立",
    "开放世界": "开放世界", "Open World": "开放世界",
    "沙盒": "沙盒", "Sandbox": "沙盒",
    "恐怖": "恐怖", "Horror": "恐怖",
    "射击": "射击", "Shooter": "射击", "FPS": "射击",
    "格斗": "格斗", "Fighting": "格斗",
    "平台游戏": "平台", "Platformer": "平台",
    "解谜": "解谜", "Puzzle": "解谜",
    "视觉小说": "视觉小说", "Visual Novel": "视觉小说",
    "生存": "生存", "Survival": "生存",
    "roguelike": "Roguelike", "Roguelike": "Roguelike",
    "动漫": "动漫", "Anime": "动漫",
    "多人": "多人", "Multiplayer": "多人",
    "合作": "合作", "Co-op": "合作",
    "卡牌": "卡牌", "Card": "卡牌",
    "模拟器": "模拟",
    "经营管理": "模拟",
}

# 缓存 app 详情（避免重复请求）
_app_detail_cache: dict[int, dict] = {}


async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict = None) -> Optional[dict]:
    """安全地抓取JSON"""
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] 请求失败: {url} — {e}")
        return None


def _parse_genre_from_tags(tags: list | None) -> str:
    """从 Steam 标签解析游戏类型"""
    if not tags:
        return ""
    seen = set()
    genres = []
    for tag, _ in tags[:10]:  # 前10个标签足够
        tag_lower = tag.lower()
        for keyword, genre in GENRE_KEYWORDS.items():
            if keyword.lower() in tag_lower and genre not in seen:
                seen.add(genre)
                genres.append(genre)
                break
    return ",".join(genres[:4])  # 最多4个类型


async def fetch_app_details(client: httpx.AsyncClient, app_id: int) -> dict | None:
    """获取单个游戏的详细数据（类型、评分等）"""
    if app_id in _app_detail_cache:
        return _app_detail_cache[app_id]

    data = await _fetch_json(client, API_APPDETAILS, {"appids": app_id, "cc": CC, "l": LANG})
    if not data or str(app_id) not in data:
        return None

    app_data = data.get(str(app_id), {}).get("data")
    if not app_data:
        return None

    # 解析类型
    genre_names = []
    if isinstance(app_data.get("tags"), dict):
        for tag_name, tag_count in app_data["tags"].items():
            if isinstance(tag_name, str):
                genre_names.append(tag_name)
    elif isinstance(app_data.get("genres"), list):
        for g in app_data["genres"]:
            if isinstance(g, dict):
                genre_names.append(g.get("description", ""))
            elif isinstance(g, str):
                genre_names.append(g)

    result = {
        "app_id": app_id,
        "name": app_data.get("name", ""),
        "genre": _parse_genre_from_tags([(n, 0) for n in genre_names]),
        "header_image": app_data.get("header_image", ""),
        "short_description": app_data.get("short_description", ""),
        "release_date": app_data.get("release_date", {}).get("date", "") if isinstance(app_data.get("release_date"), dict) else "",
        "developers": ",".join(app_data.get("developers", []) or []),
        "publishers": ",".join(app_data.get("publishers", []) or []),
        "metacritic_score": (app_data.get("metacritic", {}) or {}).get("score", 0),
    }

    _app_detail_cache[app_id] = result
    return result


async def fetch_steam_reviews(app_id: int) -> int:
    """获取 Steam 好评率（百分比）"""
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    params = {"json": 1, "language": "schinese", "purchase_type": "all", "num_per_page": 0}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            summary = data.get("query_summary", {})
            total = summary.get("total_reviews", 0) or 0
            positive = summary.get("total_positive", 0) or 0
            if total > 0:
                return round(positive / total * 100)
    except Exception:
        pass
    return 0


async def fetch_featured_deals() -> list[dict]:
    """从 featuredcategories API 获取特色折扣"""
    deals = []
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _fetch_json(client, API_FEATURED, {"cc": CC, "l": LANG})
        if not data:
            return deals

        # specials 区块
        specials = (data.get("specials", {}) or {}).get("items", []) or []
        print(f"[Steam] 特色折扣: {len(specials)} 条")

        for item in specials:
            if not item.get("discount_percent", 0):
                continue
            deal = {
                "app_id": item["id"],
                "name": item.get("name", ""),
                "name_cn": "",
                "short_description": "",
                "original_price": (item.get("original_price", 0) or 0) / 100,
                "final_price": (item.get("final_price", 0) or 0) / 100,
                "discount_percent": item.get("discount_percent", 0) or 0,
                "header_image": item.get("header_image", ""),
                "steam_rating_percent": 0,
                "genre": "",
            }

            # 获取好评率和类型
            details = await fetch_app_details(client, item["id"])
            if details:
                deal["genre"] = details.get("genre", "")
                deal["header_image"] = details.get("header_image", "") or deal["header_image"]
                if details.get("name") and details["name"] != deal["name"]:
                    deal["name_cn"] = details["name"]
                if details.get("short_description"):
                    deal["short_description"] = details["short_description"]

            # 获取好评率
            rating = await fetch_steam_reviews(item["id"])
            deal["steam_rating_percent"] = rating

            deals.append(deal)

    return deals


async def fetch_more_deals(client: httpx.AsyncClient, limit: int = 30) -> list[dict]:
    """从商店搜索页获取更多折扣游戏"""
    deals = []
    url = f"{STEAM_STORE}/search/"
    params = {"specials": 1, "cc": CC, "l": LANG, "filter": "globaltopsellers", "page": 1}

    try:
        resp = await client.get(url, params=params, timeout=20,
                                headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text

        # 找所有 search result row 的起始位置
        matches = list(re.finditer(
            r'<a\s+[^>]*data-ds-appid="(\d+)"[^>]*class="search_result_row[^"]*"[^>]*>',
            text
        ))
        print(f"[Steam] 商店搜索页找到 {len(matches)} 条折扣游戏")

        fetched = 0
        for m in matches:
            if fetched >= limit:
                break

            app_id = int(m.group(1))
            start = m.start()
            end_pos = text.find('</a>', start)
            if end_pos < 0:
                continue
            row = text[start:end_pos + 4]

            # 提取游戏名
            name_match = re.search(r'<span class="title">(.*?)</span>', row)
            name = name_match.group(1).strip() if name_match else ""

            # 提取折扣
            disc_match = re.search(r'<div class="discount_pct"[^>]*>(-?\d+)%', row)
            discount = abs(int(disc_match.group(1))) if disc_match else 0
            if not discount:
                continue

            # 提取价格（去重后取前两个）
            prices = re.findall(r'¥(\d+\.?\d*)', row)
            unique_prices = list(dict.fromkeys(prices))  # 去重保持顺序
            orig_price = float(unique_prices[0]) if len(unique_prices) >= 1 else 0
            final_price = float(unique_prices[1]) if len(unique_prices) >= 2 else 0
            if not unique_prices:
                if "Free" in row or "免费" in row:
                    continue

            # 获取详细数据
            details = await fetch_app_details(client, app_id)
            rating = await fetch_steam_reviews(app_id)

            deal = {
                "app_id": app_id,
                "name": name,
                "name_cn": details.get("name", "") if details and details.get("name") != name else "",
                "short_description": details.get("short_description", "") if details else "",
                "original_price": orig_price,
                "final_price": final_price,
                "discount_percent": discount,
                "header_image": details.get("header_image", "") if details else "",
                "steam_rating_percent": rating,
                "genre": details.get("genre", "") if details else "",
            }
            deals.append(deal)
            fetched += 1

    except Exception as e:
        print(f"[WARN] 商店搜索页解析失败: {e}")

    return deals


async def fetch_all_deals(include_more: bool = True) -> list[dict]:
    """抓取所有折扣数据（主入口）"""
    seen_app_ids = set()
    all_deals = []

    # 1. 特色折扣（来自 featuredcategories API）
    featured = await fetch_featured_deals()
    for d in featured:
        if d["app_id"] not in seen_app_ids:
            seen_app_ids.add(d["app_id"])
            all_deals.append(d)

    # 2. 更多折扣（从商店搜索页）
    if include_more:
        async with httpx.AsyncClient(timeout=30) as client:
            more = await fetch_more_deals(client, limit=40)
            for d in more:
                if d["app_id"] not in seen_app_ids and d["discount_percent"] > 0:
                    seen_app_ids.add(d["app_id"])
                    all_deals.append(d)

    # 去重并排序：按值得买指数
    for d in all_deals:
        d["worth_index"] = round((d.get("steam_rating_percent", 0) or 0) * (d.get("discount_percent", 0) or 0) / 100, 1)

    all_deals.sort(key=lambda x: x["worth_index"], reverse=True)

    print(f"[Steam] 总计获取 {len(all_deals)} 条折扣")
    return all_deals


async def main():
    """供命令行调用的入口"""
    from app.database import init_db, save_daily_deals

    print("=" * 50)
    print("Steam 折扣抓取器 v1.0")
    print(f"日期: {date.today().isoformat()}")
    print("=" * 50)

    init_db()
    deals = await fetch_all_deals(include_more=True)

    print(f"\n处理 {len(deals)} 条折扣...")
    today = date.today().isoformat()
    save_daily_deals(deals, today)

    # 打印摘要
    top = sorted([d for d in deals if d.get("worth_index", 0) > 0],
                 key=lambda x: x["worth_index"], reverse=True)[:10]
    print(f"\n🔥 今日精选 Top 10:")
    for i, d in enumerate(top, 1):
        print(f"  {i}. {d['name']}  -{d['discount_percent']}%  ¥{d['final_price']:.0f}  好评{d.get('steam_rating_percent', '?')}%  指数{d['worth_index']}")

    bargains = [d for d in deals if d.get("final_price", 999) <= 10]
    print(f"\n🥬 白菜价 (≤¥10): {len(bargains)} 款")

    return deals


if __name__ == "__main__":
    asyncio.run(main())
