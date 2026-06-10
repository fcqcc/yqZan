#!/usr/bin/env python3
"""生成每日 Steam 好价日报 — 公众号图文 + 封面图"""
import sys, os, json, time, httpx, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from collections import Counter

from app.database import get_today_top_deals, get_bargain_deals, get_today_deals, get_cover_deals
from app.wechat_push import _build_article_body
from app.game_names import GAME_NAMES
from app.translator import translate_deals

DESKTOP = "C:/Users/72770/Desktop"
DASHSCOPE_KEY = "sk-40e9946592e240d698de9041356f5d05"


def _center_crop(img, target_w, target_h):
    """Center-crop like CSS object-fit: cover"""
    from PIL import Image
    g_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if g_ratio > target_ratio:
        # 原图更宽 → 按高度缩放，裁左右
        new_w = int(target_h * g_ratio)
        img = img.resize((new_w, target_h), Image.LANCZOS)
        crop_x = (new_w - target_w) // 2
        img = img.crop((crop_x, 0, crop_x + target_w, target_h))
    else:
        # 原图更高 → 按宽度缩放，裁上下
        new_h = int(target_w / g_ratio)
        img = img.resize((target_w, new_h), Image.LANCZOS)
        crop_y = (new_h - target_h) // 2
        img = img.crop((0, crop_y, target_w, crop_y + target_h))
    return img


def gen_cover_image(fetched_date: str, total: int, bargains: int, big_sales: int,
                    top_game_name: str, top_game_discount: int, top_game_price: float,
                    top_game_image: str = "", top_deals: list = None):
    """封面 - 参考640.png风格：大标题+统计+橙线+四卡+底部域名，900x383"""
    from PIL import Image, ImageDraw, ImageFont
    import io, httpx, os, math
    path = os.path.join(DESKTOP, "steam_日报封面.png")

    # 下载前4款游戏封面
    game_imgs = []
    if top_deals:
        for d in top_deals[:4]:
            url = d.get("header_image", "")
            if url:
                try:
                    r = httpx.get(url, timeout=10)
                    if r.status_code == 200:
                        game_imgs.append(Image.open(io.BytesIO(r.content)))
                        continue
                except: pass
            game_imgs.append(None)

    W, H = 900, 383
    bg = (18, 18, 18)
    img = Image.new('RGB', (W, H), bg)
    draw = ImageDraw.Draw(img)

    # ── 字体 ──
    font_paths = [
        os.path.expanduser("~/.fonts/NotoSansCJK-Regular.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        "C:/Windows/Fonts/NotoSansSC-Regular.otf",
    ]
    font_file = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_file = fp
            break
    try:
        if font_file:
            meta_f = ImageFont.truetype(font_file, 10)
            title_f = ImageFont.truetype(font_file, 24)
            sub_f = ImageFont.truetype(font_file, 12)
            font = ImageFont.truetype(font_file, 12)
            price_f = ImageFont.truetype(font_file, 14)
            disc_f = ImageFont.truetype(font_file, 16)
            copy_f = ImageFont.truetype(font_file, 9)
        else:
            meta_f = title_f = sub_f = font = price_f = disc_f = copy_f = ImageFont.load_default()
    except:
        meta_f = title_f = sub_f = font = price_f = disc_f = copy_f = ImageFont.load_default()

    def tw(text, font):
        return draw.textlength(text, font=font)

    WHITE = (255, 255, 255)
    ACCENT = (255, 152, 0)
    RED = (255, 55, 40)
    GRAY = (150, 150, 150)
    DARK_GRAY = (180, 180, 180)

    # ── 统计 ──
    max_disc = max((d.get('discount_percent', 0) for d in (top_deals or [])[:4]), default=0)
    max_disc_all = max((d.get('discount_percent', 0) for d in (top_deals or [])), default=0)

    # ── 1. 顶部信息区 ──
    margin = 36
    # 第1行: 元信息
    dt_parts = fetched_date.split("-")
    date_label = f"{dt_parts[0]}-{dt_parts[1]}-{dt_parts[2]}"
    meta_text = f"STEAM DEALS  ·  {date_label}"
    draw.text((margin, 14), meta_text, fill=GRAY, font=meta_f)

    # 第2行: 主标题
    title_text = "Steam 好价日报"
    draw.text((margin, 34), title_text, fill=WHITE, font=title_f)

    # 第3行: 统计副标题
    sub_text = f"{total} 款折扣  ·  最高 −{max_disc_all}% OFF"
    draw.text((margin, 66), sub_text, fill=DARK_GRAY, font=sub_f)

    # 橙色装饰线
    line_y = 88
    line_len = min(240, tw(title_text, title_f))
    draw.line([(margin, line_y), (margin + line_len, line_y)], fill=ACCENT, width=2)

    # ── 2. 四卡布局 ──
    card_gap = 14
    card_w = (W - 2 * margin - 3 * card_gap) // 4  # ~198px
    img_h = int(card_w * 0.62)  # ~123px
    cards_y = line_y + 12  # 橙线下方

    # 找最高折扣确定红色
    discounts = [d.get('discount_percent', 0) for d in (top_deals or [])[:4]]
    max_disc_in_cards = max(discounts) if discounts else 0

    for i in range(4):
        x = margin + i * (card_w + card_gap)
        y = cards_y
        d = top_deals[i] if top_deals and i < len(top_deals) else {}
        disc = d.get('discount_percent', 0)
        tag_color = RED if disc == max_disc_in_cards and disc > 0 else ACCENT

        # 卡片背景
        draw.rectangle([x, y, x + card_w, y + img_h], fill=(30, 30, 30))

        # 游戏封面 center-crop
        if i < len(game_imgs) and game_imgs[i] is not None:
            try:
                gi = _center_crop(game_imgs[i], card_w, img_h)
                img.paste(gi, (x, y))
            except:
                pass

        # 折扣标签（右下角浮图）
        if disc:
            disc_text = f"−{disc}%"
            dw = tw(disc_text, disc_f)
            tag_w = dw + 12
            draw.rectangle([x + card_w - tag_w - 3, y + img_h - 28,
                           x + card_w - 3, y + img_h - 4], fill=tag_color)
            draw.text((x + card_w - tag_w + 2, y + img_h - 25),
                      disc_text, fill=WHITE, font=disc_f)

        # 游戏名（中文优先）
        name = d.get("name_cn", "") or d.get("name", "")
        if len(name) > 10:
            name = name[:9] + "…"
        draw.text((x, y + img_h + 6), name, fill=WHITE, font=font)

        # 原价（删除线）
        orig = d.get("original_price", 0) or 0
        final = d.get("final_price", 0) or 0
        if orig and final:
            otext = f"¥{orig:.0f}"
            ow = tw(otext, font)
            py = y + img_h + 24
            draw.text((x, py), otext, fill=GRAY, font=font)
            draw.line([(x, py + 7), (x + ow, py + 7)], fill=GRAY, width=1)
            # 现价
            ftext = f"¥{final:.0f}"
            draw.text((x, py + 16), ftext, fill=ACCENT, font=price_f)

    # ── 3. 底部版权 ──
    footer = "STEAM DAILY  ·  每周折扣精选  ·  yqzan.cn/steam"
    draw.text((margin, H - 15), footer, fill=(100, 100, 100), font=copy_f)

    img.save(path, 'PNG')
    print(f"[封面] ✅ {path} 参考640.png风格")
    return path

def gen_article_html(fetched_date: str, html_body: str, title: str, digest: str):
    """生成可复制到公众号编辑器的 HTML 预览文件"""
    html = f'''<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, 'PingFang SC', sans-serif; max-width: 600px; margin: 0 auto; padding: 16px; background: #f5f5f5; }}
.bar {{ background: #58a6ff; color: #fff; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; text-align: center; }}
.article {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
h1 {{ font-size: 20px; margin-bottom: 4px; }}
.meta {{ color: #999; font-size: 12px; margin-bottom: 16px; }}
.author {{ color: #666; font-size: 13px; margin-bottom: 12px; }}
.content {{ font-size: 15px; line-height: 1.7; color: #333; }}
.content h2 {{ font-size: 17px; margin: 20px 0 10px; }}
</style></head><body>
<div class="bar">📋 将下方内容复制到公众号编辑器发布</div>
<div class="article">
<h1>{title}</h1>
<div class="meta">{digest}</div>
<div class="author">✍️ 游戏好价精选</div>
<div class="content">{html_body}</div>
</div>
</body></html>'''

    path = os.path.join(DESKTOP, "steam_日报全文.html")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[全文] ✅ {path}")
    return path


def gen_daily_report(fetched_date: str | None = None):
    """一站式生成日报所有文件"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()

    print(f"📰 生成 Steam 好价日报 — {fetched_date}")
    print("=" * 40)

    # 读取数据
    top = get_today_top_deals(10, fetched_date)
    bargains = get_bargain_deals(fetched_date, 20)
    deals = get_today_deals(fetched_date)

    # 补全中文名（从对照表）
    for lst in [top, bargains, deals]:
        for i, d in enumerate(lst):
            name = d.get("name", "")
            if not d.get("name_cn") and name in GAME_NAMES:
                d = dict(d)
                d["name_cn"] = GAME_NAMES[name]
                lst[i] = d

    if not deals:
        print("❌ 没有数据，请先运行抓取")
        return

    # 智能翻译中文名和简介
    print("🌐 翻译游戏名和简介...")
    translate_deals(top)
    translate_deals(bargains)

    total = len(deals)
    bargain_count = sum(1 for d in deals if d.get("final_price", 0) <= 10)
    big_sales = sum(1 for d in deals if d.get("discount_percent", 0) >= 70)

    # 类型统计
    genre_count = Counter()
    for d in deals:
        for g in (d.get("genre", "") or "").split(","):
            g = g.strip()
            if g:
                genre_count[g] += 1
    genres = [{"genre": g, "count": c} for g, c in genre_count.most_common(8)]

    # 生成文章内容
    stats = {"total": total, "bargains": bargain_count, "big_sales": big_sales}
    article_data = _build_article_body(top, bargains, stats, genres, fetched_date)
    article = article_data["articles"][0]

    # 生成封面图 — 新游优先
    cover_deals = get_cover_deals(4, fetched_date)
    gen_cover_image(
        fetched_date, total, bargain_count, big_sales,
        cover_deals[0]["name"] if cover_deals else "",
        cover_deals[0].get("discount_percent", 0) if cover_deals else 0,
        cover_deals[0].get("final_price", 0) if cover_deals else 0,
        cover_deals[0].get("header_image", "") if cover_deals else "",
        cover_deals
    )

    # 生成文章 HTML
    gen_article_html(fetched_date, article["content"], article["title"], article["digest"])
    
    # 生成公众号可直接复制的纯内容文件（全 inline style，无 style 标签）
    raw_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{article['title']}</title></head><body>
<h1 style="font-size:22px;font-weight:700;color:#333;">{article['title']}</h1>
<div style="color:#999;font-size:12px;margin:8px 0 20px;">{article['digest']}</div>
{article['content']}
</body></html>"""
    raw_path = os.path.join(DESKTOP, "steam_文章内容_复制用.html")
    with open(raw_path, 'w', encoding='utf-8') as f:
        f.write(raw_html)
    print(f"[文章] ✅ {raw_path}")

    print(f"\n📊 数据摘要: {total} 款 | {bargain_count} 款白菜价 | {big_sales} 款超低价")
    print("\n👉 桌面已生成文件:")
    print("   1. steam_日报封面.png — 上传到公众号做封面")
    print("   2. steam_日报全文.html — 预览效果")
    print("   3. steam_文章内容_复制用.html — 直接复制到公众号编辑器")
    print("\n📋 发布步骤:")
    print("   1. 打开公众号后台 → 新建图文")
    print("   2. 上传封面图")
    print("   3. 打开 文章内容_复制用.html → 全选复制 → 公众号编辑器粘贴")
    print("   4. 标题已自动生成在内容顶部，复制过去即可")
    print("   5. 发布")


if __name__ == "__main__":
    gen_daily_report()
