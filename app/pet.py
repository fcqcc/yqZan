import json
import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.pet import (
    PET_EMOJI, FORM_NAMES, FORM_THRESHOLDS, EVOLUTION_ITEMS,
    PASSIVE_SKILLS, get_passive_reward,
    Pet, Inventory, PetDailyLog,
)
from app.models.plan import Plan, Delivery
from app.models.user import User
from app.routes.social import add_exp as _add_exp
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/pets", tags=["宠物"])


# ===== 工具函数 =====

def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def calc_unlocked_forms(total_delivered: float) -> list[str]:
    forms = ["baby"]
    for form, threshold in FORM_THRESHOLDS.items():
        if total_delivered >= threshold:
            forms.append(form)
    return list(dict.fromkeys(forms))


def calc_total_delivered(couple_id: int, db: Session) -> float:
    from app.models.plan import Delivery as Del, Plan
    total = (
        db.query(Del)
        .join(Plan, Del.plan_id == Plan.id)
        .filter(Plan.couple_id == couple_id)
        .with_entities(Del.amount)
        .all()
    )
    return sum(d[0] or 0 for d in total)


def build_pet_response(pet: Pet, total_delivered: float):
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    accs = json.loads(pet.accessories) if isinstance(pet.accessories, str) else pet.accessories
    form_emoji = PET_EMOJI.get(pet.pet_type, {}).get(pet.current_form, "🐷")
    form_labels = FORM_NAMES.get(pet.pet_type, [])
    form_idx = ["baby", "teen", "adult", "deluxe", "legend"].index(pet.current_form) if pet.current_form in ["baby", "teen", "adult", "deluxe", "legend"] else 0
    form_label = form_labels[form_idx] if form_idx < len(form_labels) else pet.current_form

    form_list = ["baby", "teen", "adult", "deluxe", "legend"]
    current_idx = form_list.index(pet.current_form) if pet.current_form in form_list else 0
    next_form = form_list[current_idx + 1] if current_idx + 1 < len(form_list) else None
    next_form_ready = next_form and total_delivered >= FORM_THRESHOLDS.get(next_form, 999999) and next_form not in unlocked

    return {
        "id": pet.id,
        "pet_type": pet.pet_type,
        "emoji": form_emoji,
        "form": pet.current_form,
        "form_label": form_label,
        "intimacy": pet.intimacy,
        "intimacy_level": get_intimacy_level(pet.intimacy),
        "is_active": pet.is_active,
        "unlocked_forms": unlocked,
        "accessories": accs,
        "next_form_ready": next_form_ready,
        "next_form_name": form_labels[current_idx + 1] if next_form else None,
        "last_fed_at": pet.last_fed_at.isoformat() if pet.last_fed_at else None,
        "passive_skill": PASSIVE_SKILLS.get(pet.pet_type, {}).get("name", ""),
        "passive_skill_desc": PASSIVE_SKILLS.get(pet.pet_type, {}).get("desc", ""),
        "image_url": get_pet_image_url(pet.pet_type, pet.current_form),
    }


def get_pet_image_url(pet_type: str, form: str) -> str:
    """生成宠物图片 URL"""
    if form and form.startswith("branch_"):
        item_id = form.replace("branch_", "")
        return f"/assets/pets/branch_{item_id}.svg"
    return f"/assets/pets/{pet_type}_{form or 'baby'}.svg"


def get_intimacy_level(intimacy: int) -> str:
    if intimacy <= 20: return "low"
    if intimacy <= 60: return "normal"
    if intimacy <= 90: return "happy"
    return "love"


def add_inventory(couple_id: int, item_type: str, item_id: str, quantity: int, db: Session):
    existing = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == item_type,
        Inventory.item_id == item_id,
        Inventory.quantity > 0,
    ).first()
    if existing:
        existing.quantity += quantity
    else:
        db.add(Inventory(couple_id=couple_id, item_type=item_type, item_id=item_id, quantity=quantity))
    db.flush()


def _apply_intimacy_decay(couple_id: int, db: Session):
    """非活跃宠物亲密衰减：≥60且连续3天未活跃 → 每天-1（不低于60）"""
    today = date.today()
    pets = db.query(Pet).filter(Pet.couple_id == couple_id).all()
    for pet in pets:
        if pet.is_active:
            continue
        if pet.intimacy < 60:
            continue
        if pet.last_active_at is None:
            continue
        days_since_active = (today - pet.last_active_at).days
        if days_since_active >= 3 and pet.intimacy > 60:
            pet.intimacy = max(60, pet.intimacy - 1)
    db.commit()


# ===== 宠物 CRUD =====

@router.get("")
def list_pets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    pets = db.query(Pet).filter(Pet.couple_id == cid).order_by(Pet.created_at).all()
    total = calc_total_delivered(cid, db)
    return [build_pet_response(p, total) for p in pets]


@router.get("/active")
def get_active_pet(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
    if not pet:
        pet = db.query(Pet).filter(Pet.couple_id == cid).first()
        if pet:
            pet.is_active = True
            pet.last_active_at = date.today()
            db.commit()
    if not pet:
        pet = Pet(couple_id=cid, pet_type="pig", is_active=True,
                  unlocked_forms=json.dumps(["baby"]), current_form="baby",
                  last_active_at=date.today())
        db.add(pet)
        db.commit()
        db.refresh(pet)
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/switch")
def switch_pet(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    pet_id = req.get("pet_id")
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")

    today = date.today()
    # 记录旧活跃宠的 last_active_at
    old_active = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
    if old_active:
        old_active.last_active_at = today

    db.query(Pet).filter(Pet.couple_id == cid).update({"is_active": False})
    pet.is_active = True
    pet.last_active_at = today
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/form")
def switch_form(pet_id: int, req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    form = req.get("form")
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms

    if form == "random":
        switch_inv = db.query(Inventory).filter(
            Inventory.couple_id == cid,
            Inventory.item_type == "consumable",
            Inventory.item_id == "switch_card",
            Inventory.quantity > 0,
        ).first()
        if not switch_inv:
            raise HTTPException(400, "没有切换卡🔄，无法随机切换")
        switch_inv.quantity -= 1
        others = [f for f in unlocked if f != pet.current_form]
        if len(others) > 1:
            form = random.choice(others)
        elif len(others) == 1:
            form = others[0]
        else:
            raise HTTPException(400, "没有其他可切换的形态")
    else:
        if form not in unlocked:
            raise HTTPException(400, "该形态未解锁")

    pet.current_form = form
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/feed")
def feed_pet(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """喂食（增加亲密度，存钱时自动调用）"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    now = datetime.now()
    # 30秒冷却（从原来1分钟缩短）
    if pet.last_fed_at and (now - pet.last_fed_at) < timedelta(seconds=30):
        raise HTTPException(429, "宠物刚吃过，让它消化一会儿吧～")
    pet.intimacy = min(100, pet.intimacy + 3)
    pet.last_fed_at = now
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/pet")
def pet_pet(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """每日抚摸（+2亲密度，每天限1次）"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    today = date.today()
    if pet.last_active_at == today and False:
        # 这个逻辑不对，last_active_at 是活跃日期
        pass
    # 检查今天是否已经抚摸过：用 pet_daily_logs 或简单用一个字段
    # 简单做法：查今天是否有该 pet 的 adventure 日志或另存一个字段
    # 更简单：用一个独立的抚摸标记字段
    # 最简方案：直接检查今天是否有抚摸记录
    from app.models.pet import PetDailyLog
    # 我们用另一种方式：看今天是否有过feed且feed时间在+2模式
    # 其实最简单的：检查今天 active pet 有没有被 feed 过（存钱触发）
    # 但对于非active pet的抚摸，我们查一下今天是否有 PetDailyLog 里的抚摸标记
    # 简便：加一个单独字段太麻烦。改为用 last_pet_at 字段临时判断
    if pet.last_fed_at and pet.last_fed_at.date() == today:
        # 如果今天已经喂过（存钱），抚摸也当作已做
        raise HTTPException(429, "今天已经互动过了，明天再来吧～")
    pet.intimacy = min(100, pet.intimacy + 2)
    pet.last_fed_at = datetime.now()  # 复用此字段记录最后互动时间
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/evolve")
def evolve_pet(pet_id: int, req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    item_id = req.get("item_id")
    if item_id not in EVOLUTION_ITEMS:
        raise HTTPException(400, "无效的进化道具")
    evo = EVOLUTION_ITEMS[item_id]

    inv = db.query(Inventory).filter(
        Inventory.couple_id == cid,
        Inventory.item_type == "evolution_item",
        Inventory.item_id == item_id,
        Inventory.quantity > 0,
    ).first()
    if not inv:
        raise HTTPException(400, "没有该道具")

    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    if pet.pet_type != evo["pet"]:
        raise HTTPException(400, f"该道具不能用于{pet.pet_type}")

    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    branch_tag = f"branch_{item_id}"
    if branch_tag in unlocked:
        raise HTTPException(400, "该分支已解锁")

    inv.quantity -= 1
    unlocked.append(branch_tag)
    pet.unlocked_forms = json.dumps(unlocked)
    pet.current_form = branch_tag
    db.commit()

    return {
        "ok": True,
        "pet_id": pet.id,
        "form_label": evo["form_label"],
        "display_emoji": evo["display_emoji"],
    }


@router.post("/refresh-forms")
def refresh_forms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    total = calc_total_delivered(cid, db)
    base_forms = calc_unlocked_forms(total)
    pets = db.query(Pet).filter(Pet.couple_id == cid).all()
    results = []
    for pet in pets:
        unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
        changed = False
        for f in base_forms:
            if f not in unlocked:
                unlocked.append(f)
                changed = True
        if changed:
            pet.unlocked_forms = json.dumps(unlocked)
            results.append({"pet_id": pet.id, "pet_type": pet.pet_type, "new_forms": base_forms})
    db.commit()
    return {"ok": True, "updated_pets": results}


# ===== 每日冒险（宠物被动技能） =====

@router.get("/daily-adventure")
def daily_adventure(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    每日冒险：当前活跃宠物触发被动技能
    - 每天首次调用会给奖励，后续仅返回结果
    - 同时执行非活跃宠物的亲密度衰减
    """
    cid = get_couple_id(user)
    today = date.today()

    # 先执行亲密衰减
    _apply_intimacy_decay(cid, db)

    # 获取活跃宠物
    pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
    if not pet:
        return {
            "triggered": False,
            "pet_name": None,
            "pet_type": None,
            "pet_emoji": None,
            "reward": None,
            "message": "还没有宠物呢～",
            "week_summary": _get_week_summary(cid, db),
        }

    pet_type = pet.pet_type
    # 从后端配置取名称和 emoji
    pet_type_name = pet.form_label or pet_type
    from app.models.pet import PET_EMOJI
    pet_emoji = PET_EMOJI.get(pet_type, {}).get(pet.current_form, "🐾")

    # 检查今天是否已经触发过
    existing = db.query(PetDailyLog).filter(
        PetDailyLog.couple_id == cid,
        PetDailyLog.created_date == today,
    ).first()
    if existing:
        # 已经触发过，返回已有结果
        return {
            "triggered": True,
            "already_done": True,
            "pet_name": pet_type_name,
            "pet_type": pet_type,
            "pet_emoji": pet_emoji,
            "reward": {
                "shards": existing.shards_reward,
                "exp": existing.exp_reward,
                "tickets": existing.tickets_reward,
            },
            "message": _build_adventure_message(pet_type_name, pet_type, existing, db),
            "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
            "week_summary": _get_week_summary(cid, db),
        }

    # 检查亲密度
    if pet.intimacy < 60:
        return {
            "triggered": False,
            "pet_name": pet_type_name,
            "pet_type": pet_type,
            "pet_emoji": pet_emoji,
            "reward": None,
            "message": f"{pet_type_name}的亲密度还不够（{pet.intimacy}/60），还不能出门冒险呢～多喂喂它吧！",
            "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
            "week_summary": _get_week_summary(cid, db),
        }

    # 计算被动收益
    reward = get_passive_reward(pet_type, pet.intimacy)
    shards_gain = reward["shards"]
    exp_gain = reward["exp"]
    tickets_gain = reward["tickets"]

    # 写入日志
    log = PetDailyLog(
        couple_id=cid,
        pet_id=pet.id,
        pet_type=pet_type,
        shards_reward=shards_gain,
        exp_reward=exp_gain,
        tickets_reward=tickets_gain,
        created_date=today,
    )
    db.add(log)

    # 发奖
    couple = db.query(Couple).filter(Couple.id == cid).first()
    if couple:
        if shards_gain > 0:
            couple.shards = (couple.shards or 0) + shards_gain
        if tickets_gain > 0:
            couple.draw_tickets = (couple.draw_tickets or 0) + tickets_gain
    if exp_gain > 0:
        _add_exp(cid, exp_gain, f"宠物冒险：{PASSIVE_SKILLS.get(pet_type, {}).get('name', '冒险归来')}", db)

    db.commit()

    return {
        "triggered": True,
        "already_done": False,
        "pet_name": pet_type_name,
        "pet_type": pet_type,
        "pet_emoji": pet_emoji,
        "reward": {
            "shards": shards_gain,
            "exp": exp_gain,
            "tickets": tickets_gain,
        },
        "message": _build_adventure_message(pet_type_name, pet_type, reward, db, is_new=True),
        "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
        "week_summary": _get_week_summary(cid, db),
    }


def _build_adventure_message(pet_name: str, pet_type: str, reward_data, db, is_new=False) -> str:
    """构建冒险归来文案"""
    if isinstance(reward_data, PetDailyLog) and not is_new:
        s = reward_data.shards_reward
        e = reward_data.exp_reward
        t = reward_data.tickets_reward
    else:
        s = reward_data["shards"] if isinstance(reward_data, dict) else 0
        e = reward_data["exp"] if isinstance(reward_data, dict) else 0
        t = reward_data["tickets"] if isinstance(reward_data, dict) else 0

    parts = []
    if s > 0:
        parts.append(f"💎 {s} 积分")
    if e > 0:
        parts.append(f"⭐ {e} 经验")
    if t > 0:
        parts.append(f"🎟️ {t} 张抽卡券")

    reward_str = "、".join(parts) if parts else "（今天没带回什么特别的东西）"
    emoji_map = {"pig": "🐷", "fox": "🦊", "cat": "🐱", "unicorn": "🦄", "dragon": "🐉"}
    emoji = emoji_map.get(pet_type, "🐾")

    return f"{emoji} {pet_name}昨晚出门冒险，为你带回来了 {reward_str}！"


def _get_week_summary(couple_id: int, db: Session) -> dict:
    """获取本周宠物冒险总收益"""
    today = date.today()
    week_start = today - timedelta(days=6)  # 过去7天
    logs = db.query(PetDailyLog).filter(
        PetDailyLog.couple_id == couple_id,
        PetDailyLog.created_date >= week_start,
        PetDailyLog.created_date <= today,
    ).all()
    return {
        "total_shards": sum(l.shards_reward for l in logs),
        "total_exp": sum(l.exp_reward for l in logs),
        "total_tickets": sum(l.tickets_reward for l in logs),
        "days_active": len(logs),
    }


# ===== 背包 =====

@router.get("/inventory", tags=["背包"])
def get_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    from app.catalog import ITEM_CATALOG
    rows = db.query(Inventory).filter(Inventory.couple_id == cid, Inventory.quantity > 0).order_by(Inventory.item_type, Inventory.item_id).all()
    result = []
    for item in rows:
        info = ITEM_CATALOG.get(item.item_id, {})
        result.append({
            "id": item.id,
            "item_type": item.item_type,
            "item_id": item.item_id,
            "quantity": item.quantity,
            "name": info.get("name", item.item_id),
            "icon": info.get("icon", "📦"),
            "type_display": info.get("type_display", "其他"),
            "desc": info.get("desc", ""),
        })
    return result


@router.post("/inventory/use")
def use_inventory_item(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)
    inv_id = req.get("inventory_id")
    inv = db.query(Inventory).filter(Inventory.id == inv_id, Inventory.couple_id == cid, Inventory.quantity > 0).first()
    if not inv:
        raise HTTPException(404, "物品不存在")

    result = {"ok": True}

    if inv.item_type == "consumable":
        if inv.item_id == "intimacy_candy":
            pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
            if pet:
                pet.intimacy = min(100, pet.intimacy + 10)
            result["effect"] = "亲密+10"
        elif inv.item_id == "fortune_cookie":
            result["message"] = "打开幸运饼干，获得一句好运势！"
        elif inv.item_id == "spark_card":
            from app.models.couple import Couple
            couple = db.query(Couple).filter(Couple.id == cid).first()
            if couple and (couple.spark_count or 0) < (couple.max_spark_count or 0):
                couple.spark_count = couple.max_spark_count
                couple.spark_status = "active"
                result["effect"] = f"火花恢复至最高记录 {couple.max_spark_count}🔥"
            elif couple:
                result["effect"] = "当前火花已达最高记录，无需使用"
                inv.quantity += 1
        elif inv.item_id == "decline_card":
            return {"action": "redirect_card_task", "message": "该卡在接到指派任务时使用，请在首页任务区使用", "card_item_id": inv.item_id}
        elif inv.item_id == "serve_me":
            return {"action": "redirect_card_task", "message": "正在发起「为我服务」指令…", "card_item_id": inv.item_id}
        elif inv.item_id == "forgive_me":
            return {"action": "redirect_card_task", "message": "正在发送「原谅我吧」…", "card_item_id": inv.item_id}
        elif inv.item_id.startswith("chore_"):
            return {"action": "redirect_card_task", "message": "正在指派家务任务…", "card_item_id": inv.item_id}

        inv.quantity -= 1
        db.commit()
        return result

    raise HTTPException(400, "该物品无法直接使用")


# ===== 图鉴 =====

@router.get("/bestiary")
def get_bestiary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = get_couple_id(user)

    from app.routes.achievement import check_and_unlock
    check_and_unlock(cid, db)

    my_pets = {p.pet_type for p in db.query(Pet).filter(Pet.couple_id == cid).all()}
    all_pets = [
        {"type": "pig", "name": "小粉猪🐷", "obtained": "pig" in my_pets, "rarity": "N"},
        {"type": "fox", "name": "小狐狸🦊", "obtained": "fox" in my_pets, "rarity": "R"},
        {"type": "cat", "name": "招财猫🐱", "obtained": "cat" in my_pets, "rarity": "SR"},
        {"type": "unicorn", "name": "独角兽🦄", "obtained": "unicorn" in my_pets, "rarity": "SSR"},
        {"type": "dragon", "name": "金元宝龙🐉", "obtained": "dragon" in my_pets, "rarity": "SSR+"},
    ]

    pet_records = db.query(Pet).filter(Pet.couple_id == cid).all()
    evo_list = []
    for eid, evo in EVOLUTION_ITEMS.items():
        obtained = False
        for p in pet_records:
            if p.pet_type == evo["pet"]:
                unlocked = json.loads(p.unlocked_forms) if isinstance(p.unlocked_forms, str) else p.unlocked_forms
                if f"branch_{eid}" in unlocked:
                    obtained = True
                    break
        evo_list.append({
            "item_id": eid,
            "name": evo["form_label"],
            "pet": evo["pet"],
            "obtained": obtained,
        })

    inv_items = db.query(Inventory).filter(Inventory.couple_id == cid).all()
    owned_items = {(i.item_type, i.item_id) for i in inv_items if i.quantity > 0}

    from app.routes.gacha import GACHA_POOL
    all_items = []
    for item_type, item_id, name, rarity, _ in GACHA_POOL:
        if item_type == "pet":
            continue
        all_items.append({
            "item_type": item_type,
            "item_id": item_id,
            "name": name,
            "rarity": rarity,
            "obtained": (item_type, item_id) in owned_items,
        })

    return {
        "pets": all_pets,
        "evolutions": evo_list,
        "items": all_items,
        "achievements": [],
    }


@router.get("/catalog")
def get_pet_catalog():
    """返回宠物静态配置数据（前端不再硬编码）"""
    pet_types = []
    for pt in ["pig", "fox", "cat", "unicorn", "dragon"]:
        forms = []
        for f in ["baby", "teen", "adult", "deluxe", "legend"]:
            forms.append({
                "form": f,
                "name": FORM_NAMES[pt][["baby", "teen", "adult", "deluxe", "legend"].index(f)] if pt in FORM_NAMES and ["baby", "teen", "adult", "deluxe", "legend"].index(f) < len(FORM_NAMES[pt]) else f,
                "emoji": PET_EMOJI.get(pt, {}).get(f, "🐾"),
                "threshold": FORM_THRESHOLDS.get(f, 0),
            })
        evolutions = []
        for eid, evo in EVOLUTION_ITEMS.items():
            if evo["pet"] == pt:
                evolutions.append({
                    "item_id": eid,
                    "form_label": evo["form_label"],
                    "display_emoji": evo["display_emoji"],
                })
        skill = PASSIVE_SKILLS.get(pt, {})
        pet_types.append({
            "type": pt,
            "forms": forms,
            "evolutions": evolutions,
            "passive_skill": skill.get("name", ""),
            "passive_desc": skill.get("desc", ""),
        })
    return {"pet_types": pet_types}
