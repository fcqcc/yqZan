import json
import random

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.pet import (
    PET_EMOJI, EVOLUTION_ITEMS,
    Pet, Inventory,
)
from app.models.plan import Delivery, Plan
from app.models.user import User
from app.routes.social import add_exp as _add_exp
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/gacha", tags=["抽卡"])


# ===== 概率表（新宠物） =====

GACHA_POOL = [
    # (item_type, item_id, name, rarity, weight)

    # ===== SSR 宠物 (4阶, 低概率) =====
    ("pet", "star_fox",    "星绒狐🦊", "SSR", 1.2),
    ("pet", "bamboo_dragon","嫩芽龙🐉", "SSR", 1.2),
    ("pet", "wave_cat",    "浪花喵🐱", "SSR", 1.2),
    ("pet", "honey_bear",  "棉花糖熊🐻", "SSR", 1.2),

    # ===== SSR 进化道具 =====
    ("evolution_item", "star_ribbon",  "星河绶带🌀", "SR", 3),
    ("evolution_item", "bamboo_sword", "青竹剑🗡️", "SR", 3),
    ("evolution_item", "sea_crown",    "神海王冠👑", "SR", 3),
    ("evolution_item", "rainbow_cape", "彩虹披风🎂", "SR", 3),

    # ===== SR 宠物 (3阶) =====
    ("pet", "dream_rabbit","绒耳兔🐰", "SR", 5),
    ("pet", "snow_deer",   "雪团鹿🦌", "SR", 5),

    # ===== R 宠物 (2阶, 高概率) =====
    ("pet", "sugar_squirrel","橡果鼠🐿️", "R", 10),
    ("pet", "lava_tanuki",   "暖炭狸🦝", "R", 10),
    ("pet", "leaf_roll",     "叶卷卷🍃", "R", 10),
    ("pet", "paper_crane",   "小纸鹤🦢", "R", 10),
    ("pet", "wind_bell",     "风铃芽🎐", "R", 10),

    # ===== 消耗品 =====
    ("consumable", "switch_card",    "切换卡🔄",   "N", 14),
    ("consumable", "intimacy_candy", "亲密糖果🍬", "N", 12),
    ("consumable", "spark_card",     "火花卡🔥",   "R", 5),
    ("consumable", "decline_card",   "我不要😤",   "R", 3),
    ("consumable", "chore_dishes",   "家务你来做之洗碗🧹", "R", 2.5),
    ("consumable", "chore_mop",      "家务你来做之拖地🧹", "R", 2.5),
    ("consumable", "chore_cook",     "家务你来做之做饭🍳", "R", 2),
    ("consumable", "chore_laundry",  "家务你来做之洗衣🧺", "R", 2),
    ("consumable", "chore_garbage",  "家务你来做之倒垃圾🗑️", "R", 1.5),
    ("background", "sakura", "樱花背景🌸", "R", 3),
    ("background", "starry", "星光背景🌟", "SR", 2),
    ("consumable", "serve_me",  "为我服务👑", "SSR", 0.8),
    ("consumable", "forgive_me","原谅我吧🥺", "SSR+", 0.2),
    ("consumable", "please_forgive_me","💎请原谅我吧💎", "SSR+", 0.08),
]

TOTAL_WEIGHT = sum(w for _, _, _, _, w in GACHA_POOL)

MAX_DRAWS_PER_DAY = 50


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def _draw_once(pity_multiplier: float = 1.0, use_boost: bool = False) -> dict:
    pool = list(GACHA_POOL)

    if pity_multiplier > 1.0 or use_boost:
        adjusted = []
        for item_type, item_id, name, rarity, weight in pool:
            w = weight
            if rarity in ("SSR", "SSR+"):
                if pity_multiplier > 1.0:
                    w = w * pity_multiplier
                if use_boost:
                    w = w * 1.5
            adjusted.append((item_type, item_id, name, rarity, w))
        pool = adjusted

    total = sum(w for _, _, _, _, w in pool)
    r = random.random() * total
    cumulative = 0.0
    for item_type, item_id, name, rarity, weight in pool:
        cumulative += weight
        if r <= cumulative:
            return {
                "item_type": item_type,
                "item_id": item_id,
                "name": name,
                "rarity": rarity,
            }
    return {"item_type": "consumable", "item_id": "intimacy_candy", "name": "亲密糖果🍬", "rarity": "N"}


def _add_draw_tickets(couple_id: int, amount: int, db: Session):
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return
    couple.draw_tickets = (couple.draw_tickets or 0) + amount
    db.commit()


def _add_crystals(couple_id: int, amount: int, db: Session):
    """添加晶石到背包"""
    existing = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "crystal",
        Inventory.item_id == "crystal",
    ).first()
    if existing:
        existing.quantity += amount
    else:
        db.add(Inventory(couple_id=couple_id, item_type="crystal", item_id="crystal", quantity=amount))
    db.flush()


# 重复宠物 → 晶石数量
CRYSTAL_PER_RARITY = {"SSR": 35, "SR": 15, "R": 5}

# 晶石兑换商店
CRYSTAL_EXCHANGE = [
    # (item_type, item_id, name, cost)
    ("evolution_item", "star_ribbon",   "星河绶带🌀", 100),
    ("evolution_item", "bamboo_sword",  "青竹剑🗡️",   100),
    ("evolution_item", "sea_crown",     "神海王冠👑", 100),
    ("evolution_item", "rainbow_cape",  "彩虹披风🎂", 100),
    ("consumable", "serve_me",   "为我服务👑", 100),
    ("consumable", "forgive_me", "原谅我吧🥺", 1000),
    ("consumable", "please_forgive_me", "💎请原谅我吧💎", 2000),
    ("consumable", "switch_card",    "切换卡🔄",   5),
    ("consumable", "intimacy_candy", "亲密糖果🍬", 10),
    ("consumable", "spark_card",     "火花卡🔥",   5),
]


def _give_item(couple_id: int, item: dict, db: Session):
    item_type = item["item_type"]
    item_id = item["item_id"]

    if item_type == "pet":
        existing = db.query(Pet).filter(
            Pet.couple_id == couple_id,
            Pet.pet_type == item_id,
        ).first()
        if existing:
            rarity = item.get("rarity", "R")
            crystal_amount = CRYSTAL_PER_RARITY.get(rarity, 10)
            _add_crystals(couple_id, crystal_amount, db)
            return {"crystals": crystal_amount, "already_owned": True}
        else:
            pet = Pet(
                couple_id=couple_id,
                pet_type=item_id,
                is_active=False,
                unlocked_forms=json.dumps(["baby"]),
                current_form="baby",
            )
            db.add(pet)
            db.flush()
            # 日志：抽到新宠物
            from app.routes.pet import _log_game_action
            _log_game_action(couple_id, "gacha", item_id,
                             f"抽到新宠物：{item.get('name', item_id)}",
                             db, item_name=item.get("name", item_id))
            return {"pet_id": pet.id, "already_owned": False}
    else:
        # 走 add_inventory 统一处理（包含进化道具限1 / 自动转晶石）
        from app.routes.pet import add_inventory, _log_game_action
        result = add_inventory(couple_id, item_type, item_id, 1, db)
        # 日志
        name = item.get("name", item_id)
        if result and result.get("converted"):
            _log_game_action(couple_id, "system_grant", item_id,
                             f"获取{name}→{result.get('crystals')}晶石💎(重复)",
                             db, item_name=name)
        else:
            _log_game_action(couple_id, "gacha", item_id,
                             f"抽到：{name}",
                             db, item_name=name)
        return result or {"already_owned": False}


def _update_pity(couple_id: int, item: dict, db: Session):
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return
    if item["rarity"] in ("SSR", "SSR+"):
        couple.gacha_pity = 0
    else:
        couple.gacha_pity = (couple.gacha_pity or 0) + 1
    db.flush()


def _get_pity_multiplier(couple_id: int, db: Session) -> float:
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return 1.0
    pity = couple.gacha_pity or 0
    if pity >= 60:
        return 3.0  # 硬保底：极高概率出SSR
    if pity >= 40:
        return 2.0
    if pity >= 20:
        return 1.5
    return 1.0


# ===== 公开 API =====


@router.get("/pool")
def get_gacha_pool(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{
        "rarity": rarity,
        "name": name,
        "pct": round(weight / TOTAL_WEIGHT * 100, 2),
        "item_type": item_type,
        "item_id": item_id,
    } for item_type, item_id, name, rarity, weight in GACHA_POOL]


@router.get("/tickets")
def get_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    return {
        "tickets": couple.draw_tickets if couple else 0,
        "shards": couple.shards if couple else 0,
        "gacha_pity": couple.gacha_pity if couple else 0,
    }


SHARDS_PER_TICKET = 100


@router.post("/buy-tickets")
def buy_tickets(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    amount = req.get("amount", 1)
    if amount not in (1, 10):
        raise HTTPException(400, "只能购买1张或10张")
    cost = SHARDS_PER_TICKET * amount
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if not couple or (couple.shards or 0) < cost:
        raise HTTPException(400, f"积分不足，需要{cost}积分（当前{couple.shards if couple else 0}积分）")
    couple.shards -= cost
    couple.draw_tickets = (couple.draw_tickets or 0) + amount
    db.commit()
    return {"ok": True, "tickets": couple.draw_tickets, "shards": couple.shards}


@router.post("/draw")
def draw_single(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if not couple or (couple.draw_tickets or 0) < 1:
        raise HTTPException(400, "抽卡券不足")

    couple.draw_tickets -= 1

    pity_mult = _get_pity_multiplier(cid, db)
    result = _draw_once(pity_multiplier=pity_mult)
    give_result = _give_item(cid, result, db)
    _update_pity(cid, result, db)

    _add_exp(cid, 2, "抽卡", db)

    db.commit()

    return {
        "item": result,
        "give_result": give_result,
        "pity_count": couple.gacha_pity or 0,
    }


@router.post("/draw10")
def draw_ten(req: dict = {}, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if not couple or (couple.draw_tickets or 0) < 10:
        raise HTTPException(400, "抽卡券不足，需要10张")

    use_boost = req.get("boost", False)
    if use_boost:
        boost_cost = 50
        if (couple.shards or 0) < boost_cost:
            raise HTTPException(400, f"积分不足，加注需要{boost_cost}积分")
        couple.shards -= boost_cost

    couple.draw_tickets -= 10

    pity_mult = _get_pity_multiplier(cid, db)

    results = []
    for _ in range(10):
        result = _draw_once(pity_multiplier=pity_mult, use_boost=use_boost)
        _give_item(cid, result, db)
        _update_pity(cid, result, db)
        results.append(result)
        _add_exp(cid, 2, "抽卡", db)

    couple.draw_tickets += 1

    db.commit()

    rarities = [r["rarity"] for r in results]
    return {
        "items": results,
        "summary": {
            "SSR+": rarities.count("SSR+"),
            "SSR": rarities.count("SSR"),
            "SR": rarities.count("SR"),
            "R": rarities.count("R"),
            "N": rarities.count("N"),
        },
        "returned_ticket": True,
        "boost_used": use_boost,
        "pity_count": couple.gacha_pity or 0,
        "shards_remaining": couple.shards or 0,
    }


# ===== 晶石系统 =====

@router.get("/crystals")
def get_crystals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取晶石余额 + 兑换商店列表"""
    cid = get_couple_id(user)
    inv = db.query(Inventory).filter(
        Inventory.couple_id == cid,
        Inventory.item_type == "crystal",
        Inventory.item_id == "crystal",
    ).first()
    balance = inv.quantity if inv else 0
    return {
        "balance": balance,
        "exchange_list": [{
            "item_type": it,
            "item_id": iid,
            "name": name,
            "cost": cost,
        } for it, iid, name, cost in CRYSTAL_EXCHANGE],
    }


@router.post("/crystals/exchange")
def exchange_crystals(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用晶石兑换物品"""
    cid = get_couple_id(user)
    item_id = req.get("item_id")
    if not item_id:
        raise HTTPException(400, "缺少 item_id")

    entry = None
    for it, iid, name, cost in CRYSTAL_EXCHANGE:
        if iid == item_id:
            entry = (it, iid, name, cost)
            break
    if not entry:
        raise HTTPException(400, "无效的兑换物品")
    item_type, item_id_val, item_name, cost = entry

    inv = db.query(Inventory).filter(
        Inventory.couple_id == cid,
        Inventory.item_type == "crystal",
        Inventory.item_id == "crystal",
    ).first()
    if not inv or inv.quantity < cost:
        raise HTTPException(400, f"晶石不足，需要{cost}晶石（当前{inv.quantity if inv else 0}晶石）")

    inv.quantity -= cost
    existing = db.query(Inventory).filter(
        Inventory.couple_id == cid,
        Inventory.item_type == item_type,
        Inventory.item_id == item_id_val,
    ).first()
    if existing:
        existing.quantity += 1
    else:
        db.add(Inventory(couple_id=cid, item_type=item_type, item_id=item_id_val, quantity=1))
    db.commit()

    return {
        "ok": True,
        "item_name": item_name,
        "crystals_remaining": inv.quantity,
    }
