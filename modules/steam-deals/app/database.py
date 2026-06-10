"""
SQLite 数据库模型 — Steam 折扣数据存储
"""
import sqlite3
import os
from datetime import date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "steam_deals.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def get_db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_db() as db:
        db.executescript("""
            -- API 密钥管理
            CREATE TABLE IF NOT EXISTS api_keys (
                api_key TEXT PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'free',
                email TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                last_used TEXT,
                is_active INTEGER DEFAULT 1
            );

            -- API 调用量日志（按月重置）
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                year_month TEXT NOT NULL,
                call_count INTEGER DEFAULT 0,
                UNIQUE(api_key, year_month)
            );

            -- 游戏元信息（去重存储）
            CREATE TABLE IF NOT EXISTS games (
                app_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                genre TEXT DEFAULT '',
                steam_rating_percent INTEGER DEFAULT 0,
                metacritic_score INTEGER DEFAULT 0,
                header_image TEXT DEFAULT '',
                release_date TEXT DEFAULT '',
                developers TEXT DEFAULT '',
                publishers TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now'))
            );

            -- 每日折扣快照
            CREATE TABLE IF NOT EXISTS daily_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                name_cn TEXT DEFAULT '',
                original_price REAL DEFAULT 0,
                final_price REAL DEFAULT 0,
                discount_percent INTEGER DEFAULT 0,
                steam_rating_percent INTEGER DEFAULT 0,
                genre TEXT DEFAULT '',
                header_image TEXT DEFAULT '',
                short_description TEXT DEFAULT '',
                worth_index REAL DEFAULT 0,
                fetched_date TEXT NOT NULL,
                is_bargain INTEGER DEFAULT 0,
                is_historic_low INTEGER DEFAULT 0,
                is_new_release INTEGER DEFAULT 0,
                UNIQUE(app_id, fetched_date)
            );

            -- 价格历史（用于判断史低）
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                final_price REAL NOT NULL,
                discount_percent INTEGER DEFAULT 0,
                record_date TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_daily_fetched ON daily_deals(fetched_date);
            CREATE INDEX IF NOT EXISTS idx_daily_discount ON daily_deals(discount_percent);
            CREATE INDEX IF NOT EXISTS idx_daily_worth ON daily_deals(worth_index);
            CREATE INDEX IF NOT EXISTS idx_daily_bargain ON daily_deals(is_bargain);
            CREATE INDEX IF NOT EXISTS idx_price_history ON price_history(app_id);
        """)


def save_daily_deals(deals: list[dict], fetched_date: str | None = None):
    """保存每日折扣快照"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()

    with get_db() as db:
        # 先清理当天已有数据避免重复
        db.execute("DELETE FROM daily_deals WHERE fetched_date = ?", (fetched_date,))

        # 检测新增折扣（前3天没出现过）
        with get_db() as check_db:
            today_ids = {(d["app_id"], d["name"]) for d in deals}
            recent_ids = set()
            for offset in range(1, 4):
                date_str = (date.today() + __import__('datetime').timedelta(days=-offset)).isoformat()
                rows = check_db.execute(
                    "SELECT app_id, name FROM daily_deals WHERE fetched_date = ?", (date_str,)
                ).fetchall()
                recent_ids.update({(r["app_id"], r["name"]) for r in rows})
            new_ids = today_ids - recent_ids
            print(f"  新增: {len(new_ids)}/{len(today_ids)} 款")

        for d in deals:
            worth = round((d.get("steam_rating_percent", 0) or 0) * (d.get("discount_percent", 0) or 0) / 100, 1)
            is_bargain = 1 if (d.get("final_price", 999) or 999) <= 10 else 0
            is_new = 1 if (d["app_id"], d["name"]) in new_ids else 0

            db.execute("""
                INSERT OR REPLACE INTO daily_deals
                (app_id, name, name_cn, original_price, final_price, discount_percent,
                 steam_rating_percent, genre, header_image, short_description, worth_index,
                 fetched_date, is_bargain, is_new_release)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["app_id"], d["name"], d.get("name_cn", ""),
                d.get("original_price", 0), d.get("final_price", 0),
                d.get("discount_percent", 0), d.get("steam_rating_percent", 0),
                d.get("genre", ""), d.get("header_image", ""), d.get("short_description", ""),
worth, fetched_date, is_bargain, is_new
            ))

            # 对比历史价格，标记史低
            cursor = db.execute("""
                SELECT MIN(final_price) as min_price FROM price_history
                WHERE app_id = ? AND record_date != ?
            """, (d["app_id"], fetched_date))
            row = cursor.fetchone()
            min_price = row["min_price"] if row and row["min_price"] is not None else 99999
            final = d.get("final_price", 99999) or 99999
            if final < min_price * 0.95:  # 比历史最低低5%就算史低
                db.execute("""
                    UPDATE daily_deals SET is_historic_low = 1
                    WHERE app_id = ? AND fetched_date = ?
                """, (d["app_id"], fetched_date))

            # 保存到价格历史
            db.execute("""
                INSERT INTO price_history (app_id, final_price, discount_percent, record_date)
                VALUES (?, ?, ?, ?)
            """, (d["app_id"], final, d.get("discount_percent", 0), fetched_date))

            # upsert games 表
            db.execute("""
                INSERT INTO games (app_id, name, name_cn, genre, steam_rating_percent, header_image, short_description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_id) DO UPDATE SET
                    name = excluded.name,
                    name_cn = CASE WHEN excluded.name_cn != '' THEN excluded.name_cn ELSE games.name_cn END,
                    genre = CASE WHEN excluded.genre != '' THEN excluded.genre ELSE games.genre END,
                    steam_rating_percent = excluded.steam_rating_percent,
                    header_image = CASE WHEN excluded.header_image != '' THEN excluded.header_image ELSE games.header_image END,
                    short_description = CASE WHEN excluded.short_description != '' THEN excluded.short_description ELSE games.short_description END,
                    updated_at = datetime('now')
            """, (
                d["app_id"], d["name"], d.get("name_cn", ""),
                d.get("genre", ""), d.get("steam_rating_percent", 0),
                d.get("header_image", ""), d.get("short_description", "")
            ))


def get_today_deals(fetched_date: str | None = None):
    """获取当天折扣数据"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM daily_deals
            WHERE fetched_date = ?
            ORDER BY worth_index DESC
        """, (fetched_date,)).fetchall()
        return [dict(r) for r in rows]


def get_today_top_deals(limit: int = 10, fetched_date: str | None = None):
    """获取当天精选 Top N"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM daily_deals
            WHERE fetched_date = ? AND worth_index > 0
            ORDER BY worth_index DESC
            LIMIT ?
        """, (fetched_date, limit)).fetchall()
        return [dict(r) for r in rows]


def get_bargain_deals(fetched_date: str | None = None, max_price: int = 20):
    """白菜价专区"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM daily_deals
            WHERE fetched_date = ? AND final_price <= ?
            ORDER BY final_price ASC, worth_index DESC
        """, (fetched_date, max_price)).fetchall()
        return [dict(r) for r in rows]


def search_deals(query: str, fetched_date: str | None = None,
                 min_discount: int = 0, max_price: float | None = None,
                 genre: str | None = None, sort_by: str = "worth",
                 limit: int = 50):
    """搜索+筛选折扣"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()

    sql = "SELECT * FROM daily_deals WHERE fetched_date = ?"
    params: list = [fetched_date]

    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if min_discount > 0:
        sql += " AND discount_percent >= ?"
        params.append(min_discount)
    if max_price is not None:
        sql += " AND final_price <= ?"
        params.append(max_price)
    if genre:
        sql += " AND genre LIKE ?"
        params.append(f"%{genre}%")

    sort_map = {
        "worth": "worth_index DESC",
        "discount": "discount_percent DESC",
        "price_asc": "final_price ASC",
        "price_desc": "final_price DESC",
        "rating": "steam_rating_percent DESC",
        "name": "name ASC",
    }
    sql += f" ORDER BY {sort_map.get(sort_by, 'worth_index DESC')} LIMIT ?"
    params.append(limit)

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_cover_deals(limit: int = 4, fetched_date: str | None = None):
    """封面用游戏：新加入的优先，其余按 worth_index 降序补齐"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    with get_db() as db:
        # 先取新增（is_new_release=1），按折扣降序
        new_rows = db.execute("""
            SELECT * FROM daily_deals
            WHERE fetched_date = ? AND is_new_release = 1 AND worth_index > 0
            ORDER BY discount_percent DESC
        """, (fetched_date,)).fetchall()
        # 取已有中 top，排除已选的 app_id
        taken_ids = set(r["app_id"] for r in new_rows)
        placeholders = ",".join("?" for _ in taken_ids) if taken_ids else "NULL"
        old_rows = db.execute(f"""
            SELECT * FROM daily_deals
            WHERE fetched_date = ? AND worth_index > 0 AND app_id NOT IN ({placeholders})
            ORDER BY worth_index DESC
            LIMIT ?
        """, (fetched_date, *taken_ids, limit)).fetchall() if len(taken_ids) < limit else []
        # 合并
        result = [dict(r) for r in new_rows] + [dict(r) for r in old_rows]
        return result[:limit]


def get_genres(fetched_date: str | None = None):
    """获取所有可用的游戏类型"""
    if fetched_date is None:
        fetched_date = date.today().isoformat()
    with get_db() as db:
        rows = db.execute("""
            SELECT DISTINCT genre FROM daily_deals
            WHERE fetched_date = ? AND genre != ''
        """, (fetched_date,)).fetchall()
        genres = set()
        for r in rows:
            for g in r["genre"].split(","):
                g = g.strip()
                if g:
                    genres.add(g)
        return sorted(genres)


# ── API Key 管理 ──────────────────────────────────────────────

import secrets
from datetime import datetime

# 套餐配额（每月调用次数）
TIER_LIMITS = {
    "free": 100,
    "basic": 1000,
    "pro": 5000,
    "unlimited": 999999,
}


def create_api_key(email: str = "", tier: str = "free") -> dict:
    """生成新 API Key"""
    api_key = "sk-" + secrets.token_hex(16)
    with get_db() as db:
        db.execute(
            "INSERT INTO api_keys (api_key, tier, email) VALUES (?, ?, ?)",
            (api_key, tier, email.strip()),
        )
    return {"api_key": api_key, "tier": tier, "limit": TIER_LIMITS.get(tier, 100)}


def validate_api_key(api_key: str) -> dict | None:
    """验证 API Key，返回 key 信息或 None"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1",
            (api_key,),
        ).fetchone()
        if not row:
            return None
        # 更新最后使用时间
        db.execute(
            "UPDATE api_keys SET last_used = ? WHERE api_key = ?",
            (datetime.now().isoformat(), api_key),
        )
        return dict(row)


def track_usage(api_key: str) -> dict:
    """记录一次调用，返回 {used, limit, remaining}"""
    now = datetime.now()
    ym = now.strftime("%Y-%m")

    with get_db() as db:
        db.execute("""
            INSERT INTO api_usage (api_key, year_month, call_count)
            VALUES (?, ?, 1)
            ON CONFLICT(api_key, year_month)
            DO UPDATE SET call_count = call_count + 1
        """, (api_key, ym))

        row = db.execute(
            "SELECT call_count FROM api_usage WHERE api_key = ? AND year_month = ?",
            (api_key, ym),
        ).fetchone()
        used = row["call_count"] if row else 0

        key_info = db.execute(
            "SELECT tier FROM api_keys WHERE api_key = ?", (api_key,),
        ).fetchone()
        limit = TIER_LIMITS.get(key_info["tier"] if key_info else "free", 100)

    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


def get_usage(api_key: str) -> dict:
    """查询当前用量"""
    now = datetime.now()
    ym = now.strftime("%Y-%m")

    with get_db() as db:
        usage = db.execute(
            "SELECT call_count FROM api_usage WHERE api_key = ? AND year_month = ?",
            (api_key, ym),
        ).fetchone()
        key_info = db.execute(
            "SELECT * FROM api_keys WHERE api_key = ?", (api_key,),
        ).fetchone()

    used = usage["call_count"] if usage else 0
    tier = key_info["tier"] if key_info else "free"
    limit = TIER_LIMITS.get(tier, 100)

    return {
        "api_key": api_key[:12] + "..." + api_key[-4:],
        "tier": tier,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "reset": "每月1日重置",
    }
