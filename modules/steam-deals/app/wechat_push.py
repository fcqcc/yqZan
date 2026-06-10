"""
微信公众平台 API 集成 — 每日好价图文推送
"""
import os
import json
import httpx
from datetime import date

from app.game_names import GAME_NAMES
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

# 加载 .env
def _load_env():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)

_load_env()

APPID = os.environ.get("WECHAT_APPID", "")
APPSECRET = os.environ.get("WECHAT_APPSECRET", "")

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/create"
PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"


async def get_access_token() -> str | None:
    """获取微信 access_token"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": APPID,
            "secret": APPSECRET,
        })
        data = resp.json()
        if "access_token" in data:
            return data["access_token"]
        print(f"[WX] 获取 token 失败: {data}")
        return None


def _build_article_body(top_deals: list[dict], bargains: list[dict],
                        stats: dict, genre_counts: list[dict],
                        fetched_date: str) -> dict:
    """构造公众号图文素材（图片+价格+玩法简介风格）"""
    body_parts = []

    # 顶部导语 + 网站入口
    body_parts.append(
        f'<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:16px;border-radius:8px;margin-bottom:16px;">'
        f'<div style="font-size:18px;font-weight:700;margin-bottom:4px;">🎮 Steam 好价日报</div>'
        f'<div style="font-size:12px;color:#aab;">📅 {fetched_date} · {stats["total"]} 款折扣</div>'
        f'<div style="margin-top:10px;font-size:12px;color:#58a6ff;">'
        f'📲 查看完整列表 & 搜索折扣 👉 <strong>yqzan.cn/steam</strong></div>'
        f'</div>'
    )

    # 精选 Top 10 — 每款：封面图 + 价格 + 玩法说明
    for i, d in enumerate(top_deals[:10], 1):
        name = d["name"]
        name_cn = d.get("name_cn", "")
        if not name_cn and name in GAME_NAMES: name_cn = GAME_NAMES[name]; d['name_cn'] = name_cn
        display_name = f"{name}（{name_cn}）" if name_cn else name
        img = d.get("header_image", "")
        price = d.get("final_price", 0)
        orig = d.get("original_price", 0)
        disc = d.get("discount_percent", 0)
        rating = d.get("steam_rating_percent", 0)
        desc = d.get("short_description", "")
        is_historic = d.get("is_historic_low", False)
        is_new = d.get("is_new_release", 0)

        historic_tag = ' <span style="background:#ffd700;color:#000;padding:1px 5px;border-radius:3px;font-size:10px;">👑史低</span>' if is_historic else ""
        rating_tag = f' <span style="background:#3fb950;color:#fff;padding:1px 4px;border-radius:3px;font-size:10px;">⭐{rating}%</span>' if rating >= 70 else ""
        new_tag = ' <span style="background:#58a6ff;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px;">🆕 今日新增</span>' if is_new else ""

        # 玩法描述 — 用 Steam 简介，标记为"🎮 玩法说明"
        if desc:
            desc_text = (
                f'<div style="background:#f0f2f5;border-left:3px solid #58a6ff;padding:8px 10px;margin:6px 0;'
                f'border-radius:4px;font-size:12px;color:#555;line-height:1.5;">'
                f'🎮 {desc[:150]}{"…" if len(desc) > 150 else ""}</div>'
            )
        else:
            desc_text = ""

        img_tag = f'<img src=\"{img}\" style=\"width:100%;height:auto;display:block;\" />' if img else ""
        body_parts.append(
            f'<div style=\"background:#f7f8fa;border-radius:8px;margin-bottom:12px;overflow:hidden;\">'
            f'{img_tag}'
            f'<div style=\"padding:10px 12px;\">'
            f'<div style=\"font-size:15px;font-weight:600;\">{display_name}{new_tag}{historic_tag}{rating_tag}</div>'
            f'{desc_text}'
            f'<div style=\"margin-top:8px;display:flex;align-items:center;justify-content:space-between;\">'
            f'<span style=\"color:#999;font-size:12px;\">原价 ¥{orig:.0f}</span>'
            f'<div style=\"text-align:right;\">'
            f'<span style=\"background:#f85149;color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;font-weight:600;\">-{disc}%</span>'
            f' <strong style=\"color:#f85149;font-size:18px;\">¥{price:.0f}</strong>'
            f'</div></div></div></div>'
        )

    # 白菜价专区
    if bargains:
        body_parts.append('<h2 style="margin:20px 0 8px;font-size:16px;">🥬 白菜价专区（≤¥20）</h2>')
        for d in bargains[:8]:
            body_parts.append(
                f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:6px 10px;margin:4px 0;font-size:13px;">'
                f'{d["name"]}'
                f' <strong style="color:#16a34a;">¥{d.get("final_price",0):.0f}</strong>'
                f' <span style="color:#999;">-{d.get("discount_percent",0)}%</span></div>'
            )

    # 底部引导 — 网页链接
    body_parts.append(
        '<div style="margin-top:28px;padding:16px;background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:8px;text-align:center;color:#fff;">'
        '<div style="font-size:15px;font-weight:700;margin-bottom:6px;">📲 查看更多折扣 & 搜索你想玩的游戏</div>'
        '<div style="font-size:22px;font-weight:900;color:#58a6ff;margin-bottom:4px;">yqzan.cn/steam</div>'
        '<div style="font-size:11px;color:#aab;">每日 06:00 更新 · 数据来源 Steam 官方 API</div>'
        '</div>'
    )

    content = "".join(body_parts)

    # 缩略图（用封面图文）
    thumb_url = ""
    if top_deals and top_deals[0].get("header_image"):
        thumb_url = top_deals[0]["header_image"]

    top_name = top_deals[0]["name"] if top_deals else ""
    top_name_cn = top_deals[0].get("name_cn", "") if top_deals else ""
    top_display = f"{top_name}（{top_name_cn}）" if top_name_cn else top_name
    top_disc = top_deals[0].get("discount_percent", 0) if top_deals else 0
    top_price = top_deals[0].get("final_price", 0) if top_deals else 0
    top_hist = "史低价" if top_deals and top_deals[0].get("is_historic_low") else ""

    title_parts = []
    if top_hist:
        title_parts.append(f"【{top_hist}】")
    title_parts.append(f"直降{top_disc}%！{top_display}仅需¥{top_price:.0f}")
    title_parts.append(f" | 今日Steam好价盘点")

    article = {
        "title": "".join(title_parts),
        "author": "游戏好价精选",
        "digest": f"今日 {stats['total']} 款折扣 · {stats['bargains']} 款白菜价 · 低至¥{min(d.get('final_price', 999) for d in (top_deals[:10] or [{}])):.0f}",
        "content": content,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    # 移除 thumb_url，避免 WeChat URL 验证问题

    return {"articles": [article]}


async def create_draft(top_deals: list[dict], bargains: list[dict],
                       stats: dict, genre_counts: list[dict],
                       fetched_date: str | None = None) -> str | None:
    """创建草稿 → 返回 media_id"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()

    token = await get_access_token()
    if not token:
        return None

    body = _build_article_body(top_deals, bargains, stats, genre_counts, fetched_date)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            DRAFT_URL,
            params={"access_token": token},
            json=body,
        )
        data = resp.json()
        if "media_id" in data:
            print(f"[WX] 草稿创建成功: media_id={data['media_id']}")
            return data["media_id"]
        else:
            print(f"[WX] 创建草稿失败: {data}")
            return None


async def publish_draft(media_id: str) -> bool:
    """发布草稿（群发）"""
    token = await get_access_token()
    if not token:
        return False

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            PUBLISH_URL,
            params={"access_token": token},
            json={"media_id": media_id},
        )
        data = resp.json()
        if data.get("errcode") == 0:
            print(f"[WX] 发布成功: publish_id={data.get('publish_id')}")
            return True
        else:
            print(f"[WX] 发布失败: {data}")
            return False


async def push_daily_report(top_deals: list[dict], bargains: list[dict],
                            stats: dict, genre_counts: list[dict],
                            fetched_date: str | None = None):
    """一站式：创建草稿 → 发布"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()

    print(f"\n📰 公众号推送 — {fetched_date}")
    print(f"   Top 10: {len(top_deals)} 条")
    print(f"   白菜价: {len(bargains)} 条")
    print(f"   游戏类型: {len(genre_counts)} 种")

    # 创建草稿
    media_id = await create_draft(top_deals, bargains, stats, genre_counts, fetched_date)
    if not media_id:
        print("[WX] ❌ 创建草稿失败，跳过发布")
        return False

    # 发布
    success = await publish_draft(media_id)
    if success:
        print(f"[WX] ✅ 公众号图文已发布")
    else:
        print(f"[WX] ❌ 发布失败")
    return success
