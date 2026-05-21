import json
import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.pet import (
    PET_EMOJI, FORM_NAMES, FORM_THRESHOLDS, EVOLUTION_ITEMS, PET_RARITY,
    PASSIVE_SKILLS, get_passive_reward,
    Pet, Inventory, PetDailyLog,
)
from app.models.plan import Plan, Delivery
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/pets", tags=["宠物"])


# ===== 工具函数 =====

def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def calc_unlocked_forms(total_delivered: float) -> list[str]:
    """根据总存款计算已解锁的常规形态"""
    forms = ["baby"]
    for form, threshold in FORM_THRESHOLDS.items():
        if total_delivered >= threshold:
            forms.append(form)
    return list(dict.fromkeys(forms))  # 去重保持顺序


def calc_total_delivered(couple_id: int, db: Session) -> float:
    """计算该 couple 的累计存款总额"""
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
    """构建宠物完整响应"""
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    accs = json.loads(pet.accessories) if isinstance(pet.accessories, str) else pet.accessories
    form_emoji = PET_EMOJI.get(pet.pet_type, {}).get(pet.current_form, "🐷")
    form_labels = FORM_NAMES.get(pet.pet_type, [])
    form_idx = ["baby", "teen", "adult", "deluxe", "legend"].index(pet.current_form) if pet.current_form in ["baby", "teen", "adult", "deluxe", "legend"] else 0
    form_label = form_labels[form_idx] if form_idx < len(form_labels) else pet.current_form

    # 可用的新形态（已解锁未获得的进化形态）
    form_list = ["baby", "teen", "adult", "deluxe", "legend"]
    current_idx = form_list.index(pet.current_form) if pet.current_form in form_list else 0
    next_form = form_list[current_idx + 1] if current_idx + 1 < len(form_list) else None
    next_form_ready = next_form and total_delivered >= FORM_THRESHOLDS.get(next_form, 999999) and next_form not in unlocked

    return {
        "id": pet.id,
        "pet_type": pet.pet_type,
        "name": form_label or pet.pet_type,
        "emoji": form_emoji,
        "form": pet.current_form,
        "form_label": form_label,
        "intimacy": pet.intimacy,
        "intimacy_max": 100,
        "intimacy_level": get_intimacy_level(pet.intimacy),
        "is_active": pet.is_active,
        "unlocked_forms": unlocked,
        "forms": [{"form": f, "name": form_labels[i] if i < len(form_labels) else f, "unlocked": f in unlocked}
                  for i, f in enumerate(["baby", "teen", "adult", "deluxe", "legend"])],
        "accessories": accs,
        "next_form_ready": next_form_ready,
        "next_form_name": form_labels[current_idx + 1] if next_form else None,
        "last_fed_at": pet.last_fed_at.isoformat() if pet.last_fed_at else None,
        "passive_skill": PASSIVE_SKILLS.get(pet.pet_type, {}).get("name", ""),
        "passive_skill_desc": PASSIVE_SKILLS.get(pet.pet_type, {}).get("desc", ""),
        "image_url": get_pet_image_url(pet.pet_type, pet.current_form),
        "rarity": PET_RARITY.get(pet.pet_type, "N"),
    }


def get_pet_image_url(pet_type: str, form: str) -> str:
    """生成宠物图片 URL"""
    return f"/assets/pets/{pet_type}_{form or 'baby'}.png"


def get_intimacy_level(intimacy: int) -> str:
    if intimacy <= 20: return "low"
    if intimacy <= 60: return "normal"
    if intimacy <= 90: return "happy"
    return "love"


def add_inventory(couple_id: int, item_type: str, item_id: str, quantity: int, db: Session):
    """向背包添加物品"""
    existing = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == item_type,
        Inventory.item_id == item_id,
    ).first()
    if existing:
        existing.quantity += quantity
    else:
        db.add(Inventory(couple_id=couple_id, item_type=item_type, item_id=item_id, quantity=quantity))
    db.flush()


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
    # 没宠物时自动创建一个默认小猪
    pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
    if not pet:
        pet = db.query(Pet).filter(Pet.couple_id == cid).first()
        if pet:
            pet.is_active = True
            db.commit()
    if not pet:
        # 初始化默认宠
        pet = Pet(couple_id=cid, pet_type="pig", is_active=True,
                  unlocked_forms=json.dumps(["baby"]), current_form="baby")
        db.add(pet)
        db.commit()
        db.refresh(pet)
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/switch")
def switch_pet(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """切换活跃宠物"""
    cid = get_couple_id(user)
    pet_id = req.get("pet_id")
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    # 把所有宠物设为非活跃，再把当前设为活跃
    db.query(Pet).filter(Pet.couple_id == cid).update({"is_active": False})
    pet.is_active = True
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/form")
def switch_form(pet_id: int, req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """切换宠物形态：必须是已解锁的，自动消耗切换卡（有则随机切换，无则自由选）"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    form = req.get("form")
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms

    if form == "random":
        # 随机切换 → 消耗切换卡
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
            import random
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
    """每日喂食（+3亲密度，每天限1次）"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    today = date.today()
    if pet.last_fed_at and pet.last_fed_at.date() == today:
        raise HTTPException(429, "今天已经喂过了，明天再来吧～")
    pet.intimacy = min(100, pet.intimacy + 3)
    pet.last_fed_at = datetime.now()
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
    if pet.last_pet_date == today:
        raise HTTPException(429, "今天已经抚摸过了，明天再来吧～")
    pet.intimacy = min(100, pet.intimacy + 2)
    pet.last_pet_date = today
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/walk")
def walk_pet(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """每日散步（+2亲密度，每天限1次）"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    today = date.today()
    if pet.last_walk_date == today:
        raise HTTPException(429, "今天已经散过步了，明天再来吧～")
    pet.intimacy = min(100, pet.intimacy + 2)
    pet.last_walk_date = today
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


@router.post("/{pet_id}/evolve")
def evolve_pet(pet_id: int, req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """使用进化道具"""
    cid = get_couple_id(user)
    item_id = req.get("item_id")
    if item_id not in EVOLUTION_ITEMS:
        raise HTTPException(400, "无效的进化道具")
    evo = EVOLUTION_ITEMS[item_id]

    # 检查道具
    inv = db.query(Inventory).filter(
        Inventory.couple_id == cid,
        Inventory.item_type == "evolution_item",
        Inventory.item_id == item_id,
        Inventory.quantity > 0,
    ).first()
    if not inv:
        raise HTTPException(400, "没有该道具")

    # 检查宠物
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    if pet.pet_type != evo["pet"]:
        raise HTTPException(400, f"该道具不能用于{pet.pet_type}")

    # 检查是否已解锁该分支（防止重复使用）
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    branch_tag = f"branch_{item_id}"
    if branch_tag in unlocked:
        raise HTTPException(400, "该分支已解锁")

    # 消耗道具
    inv.quantity -= 1

    # 解锁分支形态（用特殊tag存储）
    unlocked.append(branch_tag)
    pet.unlocked_forms = json.dumps(unlocked)

    # 分支形态使用对应的 emoji 展示
    pet.current_form = branch_tag
    db.commit()

    return {
        "ok": True,
        "pet_id": pet.id,
        "form_label": evo["form_label"],
        "display_emoji": evo["display_emoji"],
    }


# ===== 刷新形态（后端定时/手动调用） =====

@router.post("/refresh-forms")
def refresh_forms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """检查所有宠物是否有新形态可解锁（根据总存款）"""
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


# ===== 背包 =====


@router.get("/inventory", tags=["背包"])
def get_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取背包所有物品（含名称/图标/分类/描述）"""
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
    """使用消耗品"""
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
                inv.quantity += 1  # 不消耗
        elif inv.item_id == "decline_card":
            result["effect"] = "你逃过了一次家务！😤"
        elif inv.item_id == "serve_me":
            partner = db.query(User).filter(
                User.couple_id == user.couple_id, User.id != user.id
            ).first()
            partner_name = partner.nickname if partner else "对方"
            result["effect"] = f"你命令{partner_name}为你服务，不得拒绝！👑"
            result["super_rare"] = True
        elif inv.item_id == "forgive_me":
            partner = db.query(User).filter(
                User.couple_id == user.couple_id, User.id != user.id
            ).first()
            partner_name = partner.nickname if partner else "对方"
            result["effect"] = f"你对{partner_name}说：原谅我吧🥺（ta的心已经软了）"
            result["super_rare"] = True
        elif inv.item_id.startswith("chore_"):
            chore_names = {
                "chore_dishes": "洗碗🧹",
                "chore_mop": "拖地🧹",
                "chore_cook": "做饭🍳",
                "chore_laundry": "洗衣🧺",
                "chore_garbage": "倒垃圾🗑️",
            }
            name = chore_names.get(inv.item_id, inv.item_id.replace("chore_", ""))
            partner = db.query(User).filter(
                User.couple_id == user.couple_id, User.id != user.id
            ).first()
            partner_name = partner.nickname if partner else "对方"
            result["effect"] = f"指派了{partner_name}去做{name}！"

        inv.quantity -= 1
        db.commit()
        return result

    raise HTTPException(400, "该物品无法直接使用")


# ===== 图鉴 =====


@router.get("/bestiary")
def get_bestiary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取图鉴：所有可获得的物品及当前解锁状态"""
    cid = get_couple_id(user)

    from app.routes.achievement import check_and_unlock
    check_and_unlock(cid, db)

    # 宠物
    my_pets = {p.pet_type for p in db.query(Pet).filter(Pet.couple_id == cid).all()}
    from app.models.pet import PET_RARITY
    all_pet_types = [
        ("star_fox", "星绒狐🦊", "SSR"),
        ("bamboo_dragon", "嫩芽龙🐉", "SSR"),
        ("wave_cat", "浪花喵🐱", "SSR"),
        ("honey_bear", "棉花糖熊🐻", "SSR"),
        ("dream_rabbit", "绒耳兔🐰", "SR"),
        ("snow_deer", "雪团鹿🦌", "SR"),
        ("wind_bell", "风铃芽🎐", "R"),
        ("sugar_squirrel", "橡果鼠🐿️", "R"),
        ("lava_tanuki", "暖炭狸🦝", "R"),
        ("leaf_roll", "叶卷卷🍃", "R"),
        ("paper_crane", "小纸鹤🦢", "R"),
    ]
    all_pets = [{"type": t, "name": n, "obtained": t in my_pets, "rarity": r} for t, n, r in all_pet_types]

    # 进化形态
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

    # 所有背包物品类型
    inv_items = db.query(Inventory).filter(Inventory.couple_id == cid).all()
    owned_items = {(i.item_type, i.item_id) for i in inv_items if i.quantity > 0}

    # 所有卡池道具（图鉴用）
    from app.routes.gacha import GACHA_POOL
    all_items = []
    for item_type, item_id, name, rarity, _ in GACHA_POOL:
        if item_type == "pet":
            continue  # 宠物在图鉴另一块
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


def _add_exp(couple_id: int, amount: int, reason: str, db):
    """给情侣增加经验"""
    from app.models.couple import Couple
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return
    from app.models.level import LevelLog
    couple.exp = (couple.exp or 0) + amount
    db.add(LevelLog(couple_id=couple_id, amount=amount, reason=reason))
    db.flush()


def _apply_intimacy_decay(couple_id: int, db):
    """非活跃宠物亲密衰减：≥60且连续3天未活跃→每天-1"""
    today = date.today()
    pets = db.query(Pet).filter(Pet.couple_id == couple_id).all()
    for pet in pets:
        if pet.is_active or pet.intimacy < 60 or pet.last_active_at is None:
            continue
        days_since = (today - pet.last_active_at).days
        if days_since >= 3 and pet.intimacy > 60:
            pet.intimacy = max(60, pet.intimacy - 1)
    db.commit()


@router.get("/daily-adventure")
def daily_adventure(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """每日冒险：活跃宠物触发被动技能"""
    cid = get_couple_id(user)
    today = date.today()
    _apply_intimacy_decay(cid, db)

    pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
    if not pet:
        return {"triggered": False, "message": "还没有宠物呢～"}

    pet_type = pet.pet_type
    form_labels = FORM_NAMES.get(pet_type, [])
    form_idx = ["baby","teen","adult","deluxe","legend"].index(pet.current_form) if pet.current_form in ["baby","teen","adult","deluxe","legend"] else 0
    pet_name = form_labels[form_idx] if form_idx < len(form_labels) else pet.current_form
    pet_emoji = PET_EMOJI.get(pet_type, {}).get(pet.current_form, "🐾")

    # 检查今日是否已触发
    existing = db.query(PetDailyLog).filter(
        PetDailyLog.couple_id == cid,
        PetDailyLog.created_date == today,
    ).first()
    if existing:
        return {
            "triggered": True, "already_done": True,
            "pet_name": pet_name, "pet_type": pet_type, "pet_emoji": pet_emoji,
            "reward": {"shards": existing.shards_reward, "exp": existing.exp_reward, "tickets": existing.tickets_reward},
            "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
            "week_summary": _get_week_summary(cid, db),
        }

    if pet.intimacy < 60:
        return {
            "triggered": False,
            "pet_name": pet_name, "pet_type": pet_type, "pet_emoji": pet_emoji,
            "reward": None,
            "message": f"亲密度还不够（{pet.intimacy}/60），还不能出门冒险～",
            "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
            "week_summary": _get_week_summary(cid, db),
        }

    reward = get_passive_reward(pet_type, pet.intimacy)
    shards_gain = reward.get("shards", 0)
    exp_gain = reward.get("exp", 0)
    tickets_gain = reward.get("tickets", 0)

    log = PetDailyLog(
        couple_id=cid, pet_id=pet.id, pet_type=pet_type,
        shards_reward=shards_gain, exp_reward=exp_gain, tickets_reward=tickets_gain,
        created_date=today,
    )
    db.add(log)

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
        "triggered": True, "already_done": False,
        "pet_name": pet_name, "pet_type": pet_type, "pet_emoji": pet_emoji,
        "reward": {"shards": shards_gain, "exp": exp_gain, "tickets": tickets_gain},
        "passive_name": PASSIVE_SKILLS.get(pet_type, {}).get("name", ""),
        "week_summary": _get_week_summary(cid, db),
    }


def _get_week_summary(couple_id: int, db) -> dict:
    """本周宠物冒险总收益"""
    today = date.today()
    week_start = today - timedelta(days=6)
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
