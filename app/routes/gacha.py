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
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/gacha", tags=["抽卡"])


# ===== 概率表（写在代码里，不走数据库） =====
# 权重制：总权重 = 100，独立概率已标出

GACHA_POOL = [
    # (item_type, item_id, name, rarity, weight)
    ("consumable", "fortune_cookie", "幸运饼干🍪", "N", 16),
    ("consumable", "switch_card", "切换卡🔄", "N", 12),
    ("consumable", "intimacy_candy", "亲密糖果🍬", "N", 10),
    ("pet", "fox", "小狐狸🦊", "R", 10),
    ("accessory", "bow", "蝴蝶结🎀", "N", 6),
    ("accessory", "sunglasses", "墨镜🕶️", "R", 5),
    ("pet", "cat", "招财猫🐱", "SR", 4),
    ("consumable", "streak_protect", "免断卡🛡️", "R", 3),
    ("evolution_item", "gold_ingot", "金元宝🪙", "SR", 3),
    ("evolution_item", "love_arrow", "爱心箭🏹", "SR", 3),
    ("evolution_item", "moon_stone", "月光石🌙", "SR", 3),
    ("evolution_item", "fortune_bell", "招财铃🎴", "SR", 3),
    ("accessory", "crown", "皇冠👑", "SR", 3),
    ("background", "sakura", "樱花背景🌸", "R", 3),
    ("consumable", "decline_card", "我不要😤", "R", 3),
    ("consumable", "chore_dishes", "家务你来做之洗碗🧹", "R", 2),
    ("consumable", "chore_mop", "家务你来做之拖地🧹", "R", 2),
    ("consumable", "chore_cook", "家务你来做之做饭🍳", "R", 1.5),
    ("consumable", "chore_laundry", "家务你来做之洗衣🧺", "R", 1.5),
    ("consumable", "chore_garbage", "家务你来做之倒垃圾🗑️", "R", 1),
    ("consumable", "reminder_horn", "提醒喇叭📣", "N", 1),
    ("background", "starry", "星光背景🌟", "SR", 2),
    ("evolution_item", "mech_core", "机械核心⚙️", "SSR", 1.5),
    ("evolution_item", "stardust", "星尘🌌", "SSR", 1.5),
    ("pet", "unicorn", "独角兽🦄", "SSR", 0.8),
    ("pet", "dragon", "金元宝龙🐉", "SSR+", 0.2),
    ("consumable", "serve_me", "为我服务👑", "SSR", 0.5),
    ("consumable", "forgive_me", "原谅我吧🥺", "SSR+", 0.1),
]

TOTAL_WEIGHT = sum(w for _, _, _, _, w in GACHA_POOL)

# 抽一次最大值
MAX_DRAWS_PER_DAY = 50  # 防刷


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def _draw_once() -> dict:
    """核心抽奖逻辑：权重制，支持小数权重"""
    total = TOTAL_WEIGHT
    r = random.random() * total
    cumulative = 0.0
    for item_type, item_id, name, rarity, weight in GACHA_POOL:
        cumulative += weight
        if r <= cumulative:
            return {
                "item_type": item_type,
                "item_id": item_id,
                "name": name,
                "rarity": rarity,
            }
    # 保底
    return {"item_type": "consumable", "item_id": "intimacy_candy", "name": "亲密糖果🍬", "rarity": "N"}


def _add_draw_tickets(couple_id: int, amount: int, db: Session):
    """添加抽卡券"""
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return
    couple.draw_tickets = (couple.draw_tickets or 0) + amount
    db.commit()


def _give_item(couple_id: int, item: dict, db: Session):
    """将抽到的物品放入背包"""
    item_type = item["item_type"]
    item_id = item["item_id"]

    if item_type == "pet":
        # 新宠物：检查是否已有
        existing = db.query(Pet).filter(
            Pet.couple_id == couple_id,
            Pet.pet_type == item_id,
        ).first()
        if existing:
            # 已有该宠物 → 给 5 张抽卡券作为补偿
            _add_draw_tickets(couple_id, 5, db)
            return {"bonus_tickets": 5, "already_owned": True}
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
            return {"pet_id": pet.id, "already_owned": False}
    else:
        # 其他物品 → 放进背包
        existing = db.query(Inventory).filter(
            Inventory.couple_id == couple_id,
            Inventory.item_type == item_type,
            Inventory.item_id == item_id,
        ).first()
        if existing:
            existing.quantity += 1
        else:
            inv = Inventory(
                couple_id=couple_id,
                item_type=item_type,
                item_id=item_id,
                quantity=1,
            )
            db.add(inv)
            db.flush()
        return {"already_owned": False}


# ===== 公开 API =====


@router.get("/tickets")
def get_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前抽卡券数量"""
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    return {"tickets": couple.draw_tickets if couple else 0}


@router.post("/draw")
def draw_single(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """单抽"""
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if not couple or (couple.draw_tickets or 0) < 1:
        raise HTTPException(400, "抽卡券不足")

    # 消耗券
    couple.draw_tickets -= 1

    # 抽
    result = _draw_once()
    give_result = _give_item(cid, result, db)
    db.commit()

    return {
        "item": result,
        "give_result": give_result,
    }


@router.post("/draw10")
def draw_ten(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """十连抽：消耗10张，返还1张"""
    cid = get_couple_id(user)
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if not couple or (couple.draw_tickets or 0) < 10:
        raise HTTPException(400, "抽卡券不足，需要10张")

    # 消耗 10 张
    couple.draw_tickets -= 10

    # 抽 10 次
    results = []
    for _ in range(10):
        result = _draw_once()
        _give_item(cid, result, db)
        results.append(result)

    # 返还 1 张
    couple.draw_tickets += 1

    db.commit()

    # 统计出货情况
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
    }
