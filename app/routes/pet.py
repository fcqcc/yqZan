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
    Pet, Inventory, PetDailyLog, ItemDailyUsage,
    EXP_PER_LEVEL, MAX_LEVEL, get_form_by_level, get_current_level_cap,
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
    # 🔥 过滤掉内部 branch_xxx 标记，不暴露给前端
    unlocked_display = [f for f in unlocked if not f.startswith('branch_')]
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

    # 🔥 判断宠物是否已经道具进化过（分支标记 branch_xxx）
    has_item_evolved = any(f.startswith('branch_') for f in unlocked)

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
        "unlocked_forms": unlocked_display,
        "forms": [{"form": f, "name": form_labels[i] if i < len(form_labels) else f, "unlocked": f in unlocked_display}
                  for i, f in enumerate(["baby", "teen", "adult", "deluxe", "legend"])],
        "accessories": accs,
        "next_form_ready": next_form_ready,
        "next_form_name": form_labels[current_idx + 1] if next_form and current_idx + 1 < len(form_labels) else None,
        "last_fed_at": pet.last_fed_at.isoformat() if pet.last_fed_at else None,
        "passive_skill": PASSIVE_SKILLS.get(pet.pet_type, {}).get("name", ""),
        "passive_skill_desc": PASSIVE_SKILLS.get(pet.pet_type, {}).get("desc", ""),
        "image_url": get_pet_image_url(pet.pet_type, pet.current_form),
        "rarity": PET_RARITY.get(pet.pet_type, "N"),
        "exp": pet.exp % EXP_PER_LEVEL,  # 当前等级内经验
        "exp_total": pet.exp,              # 总经验
        "level": pet.level,
        "evolution_ready": False if has_item_evolved else pet.evolution_ready,
        "has_item_evolved": has_item_evolved,
        "max_level": get_current_level_cap(pet),  # 动态上限
        "exp_needed": EXP_PER_LEVEL,  # 每级固定需要4点
    }


def get_pet_image_url(pet_type: str, form: str) -> str:
    """生成宠物图片 URL（找不到时降级到最高可用形态）"""
    import os
    BASE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "pets")
    # 按形态优先级降级查找
    FORM_FALLBACK = ["legend", "deluxe", "adult", "teen", "baby"]
    start = FORM_FALLBACK.index(form) if form in FORM_FALLBACK else len(FORM_FALLBACK) - 1
    for f in FORM_FALLBACK[start:]:
        path = f"{pet_type}_{f}.png"
        if os.path.exists(os.path.join(BASE, path)):
            return f"/assets/pets/{path}"
    # 兜底
    return f"/assets/pets/{pet_type}_baby.png"


def get_intimacy_level(intimacy: int) -> str:
    if intimacy <= 20: return "low"
    if intimacy <= 60: return "normal"
    if intimacy <= 90: return "happy"
    return "love"


def add_inventory(couple_id: int, item_type: str, item_id: str, quantity: int, db: Session):
    """向背包添加物品（进化道具限1个，超出自动转晶石）"""
    # 进化道具检查：已拥有 或 宠物已解锁对应分支 → 转晶石
    from app.models.pet import EVOLUTION_ITEMS, Pet
    if item_type == "evolution_item" and item_id in EVOLUTION_ITEMS:
        existing = db.query(Inventory).filter(
            Inventory.couple_id == couple_id,
            Inventory.item_type == item_type,
            Inventory.item_id == item_id,
            Inventory.quantity > 0,
        ).first()
        if existing:
            # 已有此道具 → 转晶石
            from app.routes.gacha import _add_crystals, CRYSTAL_PER_RARITY
            amt = CRYSTAL_PER_RARITY.get("SSR", 35)
            _add_crystals(couple_id, amt, db)
            _log_game_action(couple_id, "system_grant", item_id,
                             f"进化道具已拥有，自动转化{amt}晶石💎", db)
            return {"converted": True, "crystals": amt, "message": f"进化道具已拥有，转化为{amt}晶石💎"}
        # 检查宠物是否已解锁该分支
        evo = EVOLUTION_ITEMS[item_id]
        branch_tag = f"branch_{item_id}"
        pet_has_branch = db.query(Pet).filter(
            Pet.couple_id == couple_id,
            Pet.pet_type == evo["pet"],
        ).filter(Pet.unlocked_forms.contains(branch_tag)).first()
        if pet_has_branch:
            from app.routes.gacha import _add_crystals, CRYSTAL_PER_RARITY
            amt = CRYSTAL_PER_RARITY.get("SSR", 35)
            _add_crystals(couple_id, amt, db)
            _log_game_action(couple_id, "system_grant", item_id,
                             f"宠物最终形态已解锁，自动转化{amt}晶石💎", db)
            return {"converted": True, "crystals": amt, "message": f"宠物已达最终形态，道具转化为{amt}晶石💎"}

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


def _log_game_action(couple_id: int, action_type: str, item_id: str, details: str, db: Session, item_name: str = ""):
    """记录游戏行为日志"""
    from app.models.social import GameLog
    from datetime import datetime
    log = GameLog(
        couple_id=couple_id,
        action_type=action_type,
        item_id=item_id,
        item_name=item_name,
        details=details,
        created_at=datetime.now(),
    )
    db.add(log)
    db.flush()


def add_exp_to_active_pet(couple_id: int, amount: int, db: Session):
    """给情侣的活跃宠物加经验，检测等级进化"""
    if amount <= 0:
        return
    from app.models.pet import EXP_PER_LEVEL, MAX_LEVEL, PET_RARITY, get_current_level_cap

    pet = db.query(Pet).filter(
        Pet.couple_id == couple_id, Pet.is_active == True
    ).first()
    if not pet:
        return

    # ❌ 进化锁定中，不能再获得经验
    if pet.evolution_ready:
        return

    rarity = PET_RARITY.get(pet.pet_type, "R")
    rarity_max = MAX_LEVEL.get(rarity, 10)  # 稀有度绝对上限
    current_cap = get_current_level_cap(pet)  # 当前形态动态上限

    # ❌ 已达当前形态上限
    if pet.level >= current_cap:
        # 如果刚好在进化门槛上（每5级），标记进化就绪
        if pet.level % 5 == 0 and pet.level < rarity_max:
            pet.evolution_ready = True
            db.flush()
        return

    # ✅ 加经验（用累计总经验法正确计算等级）
    from app.models.pet import EXP_PER_LEVEL as EPL
    old_level = pet.level
    exp_at_old = (old_level - 1) * EPL  # 升到当前级已消耗的总经验
    total_exp = exp_at_old + (pet.exp or 0) + amount  # 累积总经验

    new_level = min(total_exp // EPL + 1, current_cap)
    pet.level = new_level

    if new_level < current_cap:
        pet.exp = total_exp - (new_level - 1) * EPL  # 本级余数
    else:
        pet.exp = 0  # 到上限清0

    # 🔔 等级变化时触发检测
    if old_level != new_level:
        pet.last_active_at = date.today()

    # ⭐ 检测是否到达进化门槛（每5级）
    if pet.level % 5 == 0 and pet.level <= current_cap and pet.level < rarity_max:
        pet.evolution_ready = True

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
        return None
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
    add_exp_to_active_pet(cid, 1, db)
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
    add_exp_to_active_pet(cid, 1, db)
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
    add_exp_to_active_pet(cid, 1, db)
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

    # ❗等级验证：必须到达当前形态满级附近（避免在10级adult形态误用）
    from app.models.pet import get_current_level_cap
    current_cap = get_current_level_cap(pet)
    if pet.level < current_cap - 1:
        raise HTTPException(400, f"等级不足！当前形态满级 {current_cap}，至少需要 {current_cap - 1} 级才能进化")

    # ❗形态验证：进化道具的目标形态的前一位必须是当前形态
    # SSR≥15级跳过此检查（直接进化到目标形态）
    rarity = PET_RARITY.get(pet.pet_type, "R")
    FORM_ORDER = ["baby", "teen", "adult", "deluxe", "legend"]
    target_form = evo.get("form", "")
    if target_form in FORM_ORDER and not (rarity == "SSR" and pet.level >= 15):
        target_idx = FORM_ORDER.index(target_form)
        required_form = FORM_ORDER[target_idx - 1] if target_idx > 0 else None
        if required_form and pet.current_form != required_form:
            raise HTTPException(400, f"当前形态「{pet.current_form}」不支持进化，需要切换到「{required_form}」形态")

    # 检查是否已解锁该分支
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    branch_tag = f"branch_{item_id}"
    if branch_tag in unlocked:
        # 🔄 分支已存在 → 消耗道具转化为晶石（SSR级35晶石）
        inv.quantity -= 1
        from app.routes.gacha import _add_crystals, CRYSTAL_PER_RARITY
        crystal_amt = CRYSTAL_PER_RARITY.get("SSR", 35)
        _add_crystals(cid, crystal_amt, db)
        evo_name = evo.get("form_label", item_id)
        from app.catalog import ITEM_CATALOG
        full_name = ITEM_CATALOG.get(item_id, {}).get("name", item_id)
        _log_game_action(cid, "evolution", item_id,
                         f"分支已存在，{full_name}→{crystal_amt}晶石💎",
                         db, item_name=full_name)
        # 🔥 先构建返回数据再提交
        result = {
            "ok": True,
            "converted": True,
            "crystals": crystal_amt,
            "message": f"分支已存在，{evo_name}转化为{crystal_amt}晶石💎",
        }
        db.commit()
        return result

    # 消耗道具
    inv.quantity -= 1

    # 解锁分支形态（用特殊tag存储，仅用于防重复检测）
    unlocked.append(branch_tag)
    # 同时把目标形态也加入已解锁，用于等级上限计算
    if target_form not in unlocked:
        unlocked.append(target_form)
    pet.unlocked_forms = json.dumps(unlocked)

    # 形态改为目标形态名（deluxe/legend），不是 branch_xxx
    pet.current_form = target_form
    # 清除进化就绪标记（最终形态不需要再进化了）
    pet.evolution_ready = False

    from app.catalog import ITEM_CATALOG
    full_name = ITEM_CATALOG.get(item_id, {}).get("name", item_id)
    _log_game_action(cid, "evolution", item_id,
                     f"使用{full_name}进化 {pet.pet_type} → {evo.get('form_label', target_form)}",
                     db, item_name=full_name)

    # 🔥 先构建返回数据再提交（防止返回时出错导致已提交的错误数据）
    result = {
        "ok": True,
        "pet_id": pet.id,
        "form_label": evo.get("form_label", target_form),
        "display_emoji": evo.get("display_emoji", "✨"),
        "current_form": target_form,
    }
    db.commit()
    return result


# ===== 等级进化（每5级手动确认）=====
@router.post("/{pet_id}/level-evolve")
def level_evolve_pet(pet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """等级进化：宠物达到每5级时手动确认进化"""
    cid = get_couple_id(user)
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.couple_id == cid).first()
    if not pet:
        raise HTTPException(404, "宠物不存在")
    if not pet.evolution_ready:
        raise HTTPException(400, "当前不可进化")

    # 🔥 SSR满15级没有等级进化（必须使用道具进化）
    rarity = PET_RARITY.get(pet.pet_type, "R")
    if rarity == "SSR" and pet.level >= 15:
        raise HTTPException(400, "SSR满15级无法等级进化，请使用「道具进化」")

    new_form = get_form_by_level(pet.level)
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    if new_form not in unlocked:
        unlocked.append(new_form)
        pet.unlocked_forms = json.dumps(unlocked)
    pet.current_form = new_form
    pet.evolution_ready = False
    db.commit()
    total = calc_total_delivered(cid, db)
    return build_pet_response(pet, total)


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
    """使用消耗品（含每日使用次数限制）"""
    from datetime import date
    cid = get_couple_id(user)
    inv_id = req.get("inventory_id")
    inv = db.query(Inventory).filter(Inventory.id == inv_id, Inventory.couple_id == cid, Inventory.quantity > 0).first()
    if not inv:
        raise HTTPException(404, "物品不存在")

    result = {"ok": True}

    # ===== 每日使用限制配置（已注释，测试模式） =====
    # DAILY_LIMITS = {
    #     "intimacy_candy": 5,
    #     "decline_card": 3,
    #     "spark_card": 1,
    #     "serve_me": 1,
    #     "forgive_me": 1,
    #     "please_forgive_me": 1,
    # }
    # CHORE_LIMIT = 3

    # 检查每日限制（已注释）
    # today = date.today()
    # limit = None
    # if inv.item_id not in ("exp_candy",):
    #     if inv.item_id in DAILY_LIMITS:
    #         limit = DAILY_LIMITS[inv.item_id]
    #     elif inv.item_id.startswith("chore_"):
    #         limit = CHORE_LIMIT

    # if limit is not None:
    #     usage = db.query(ItemDailyUsage).filter(
    #         ItemDailyUsage.user_id == user.id,
    #         ItemDailyUsage.item_id == inv.item_id,
    #         ItemDailyUsage.use_date == today,
    #     ).first()
    #     used = usage.use_count if usage else 0
    #     if used >= limit:
    #         raise HTTPException(429, f"今日已使用{used}次，已达上限{limit}次")
    #     if usage:
    #         usage.use_count += 1
    #     else:
    #         db.add(ItemDailyUsage(user_id=user.id, item_id=inv.item_id, use_date=today, use_count=1))

    if inv.item_type == "consumable":
        if inv.item_id == "intimacy_candy":
            # 所有已拥有宠物 +5 亲密度
            pets = db.query(Pet).filter(Pet.couple_id == cid).all()
            affected = 0
            for pet in pets:
                if pet.intimacy < 100:
                    pet.intimacy = min(100, pet.intimacy + 5)
                    affected += 1
            result["effect"] = f"所有宠物亲密度+5（{affected}只已增加）😊"
        elif inv.item_id == "fortune_cookie":
            result["message"] = "打开幸运饼干，获得一句好运势！"
        elif inv.item_id == "exp_candy":
            # 经验糖果：给活跃宠物+1000EXP（满级不消耗）
            from app.models.pet import MAX_LEVEL, EXP_PER_LEVEL, PET_RARITY, get_current_level_cap
            pet = db.query(Pet).filter(Pet.couple_id == cid, Pet.is_active == True).first()
            if not pet:
                raise HTTPException(400, "没有活跃宠物")
            rarity = PET_RARITY.get(pet.pet_type, "R")
            max_lv = get_current_level_cap(pet)  # 动态上限
            if pet.level >= max_lv:
                result["effect"] = "当前宠物已达形态上限，先进化再来使用吧！"
                inv.quantity += 1  # 不消耗
            else:
                old_lv = pet.level
                add_exp_to_active_pet(cid, 1000, db)
                new_lv = pet.level
                if new_lv == old_lv:
                    result["effect"] = "经验已满，先进化再使用糖果吧！"
                    inv.quantity += 1  # 不消耗
                else:
                    result["effect"] = f"活跃宠物经验+1000！等级{old_lv}→{new_lv} 🎉"
            result["_no_limit"] = True  # 不受每日限制
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
        inv.quantity -= 1

        # ===== 卡牌类物品 → 创建 CardTask（复用 card_task 模块） =====
        from app.routes.card_task import CARD_NAMES, check_conflict
        from app.models.card_task import CardTask

        if inv.item_id in CARD_NAMES and inv.item_id != "decline_card":
            partner = db.query(User).filter(
                User.couple_id == user.couple_id, User.id != user.id
            ).first()
            if not partner:
                inv.quantity += 1  # 不消耗，退回
                raise HTTPException(400, "伴侣不存在")
            partner_name = partner.nickname or "对方"
            card_name = CARD_NAMES.get(inv.item_id, inv.item_id)

            # 检查同类型冲突
            try:
                check_conflict(cid, inv.item_id, db)
            except HTTPException:
                inv.quantity += 1  # 冲突了也不要消耗
                raise

            task = CardTask(
                couple_id=cid,
                card_item_id=inv.item_id,
                card_name=card_name,
                assigner_id=user.id,
                assignee_id=partner.id,
                status="pending",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            _log_game_action(cid, "card_use", inv.item_id,
                             f"使用{card_name}：指派{partner_name}",
                             db, item_name=card_name)

            if inv.item_id == "serve_me":
                result["effect"] = f"你命令{partner_name}为你服务，不得拒绝！👑"
                result["super_rare"] = True
            elif inv.item_id == "forgive_me":
                result["effect"] = f"你对{partner_name}说：原谅我吧🥺"
                result["super_rare"] = True
            else:
                result["effect"] = f"指派了{partner_name}去做{card_name}！"
        else:
            # decline_card → 仅提示，不创建任务
            if inv.item_id == "decline_card":
                result["effect"] = "你逃过了一次家务！😤"

        from app.catalog import ITEM_CATALOG
        item_info = ITEM_CATALOG.get(inv.item_id, {})
        item_name = item_info.get("name", inv.item_id)
        card_name = CARD_NAMES.get(inv.item_id, "")
        use_name = item_name or card_name or inv.item_id
        eff = result.get("effect", "")
        _log_game_action(cid, "item_use", inv.item_id,
                         f"使用{use_name}：{eff}",
                         db, item_name=use_name)
        db.commit()
        return result

    raise HTTPException(400, "该物品无法直接使用")


# ===== 宠物图鉴/目录 =====


@router.get("/catalog")
def get_pet_catalog(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有宠物类型配置"""
    from app.models.pet import PET_RARITY, FORM_NAMES, PET_EMOJI
    pet_types = []
    for ptype, rarity in PET_RARITY.items():
        names = FORM_NAMES.get(ptype, [])
        emojis = PET_EMOJI.get(ptype, {})
        pet_types.append({
            "type": ptype,
            "rarity": rarity,
            "form_names": names,
            "emojis": {k: v for k, v in emojis.items()},
        })
    return {"pet_types": pet_types}


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

    # 检查今日是否已触发（优先于其他逻辑）
    existing_log = db.query(PetDailyLog).filter(
        PetDailyLog.couple_id == cid,
        PetDailyLog.created_date == today,
    ).first()
    if existing_log and existing_log.pet_type:
        pet_type = existing_log.pet_type
        passive_name = PASSIVE_SKILLS.get(pet_type, {}).get("name", "")
        form_labels = FORM_NAMES.get(pet_type, [])
        return {
            "triggered": True, "already_done": True,
            "pet_name": form_labels[0] if form_labels else pet_type,
            "pet_type": pet_type,
            "pet_emoji": PET_EMOJI.get(pet_type, {}).get("legend", "🐾"),
            "reward": {"shards": existing_log.shards_reward, "exp": existing_log.exp_reward, "tickets": existing_log.tickets_reward},
            "passive_name": passive_name,
            "week_summary": _get_week_summary(cid, db),
        }

    # 🔥 查找所有好感度≥60的宠物，选形态最高者计算被动奖励
    from sqlalchemy import text
    FORM_ORDER = ["baby", "teen", "adult", "deluxe", "legend"]
    all_pets = db.query(Pet).filter(Pet.couple_id == cid).all()
    best_pet = None          # 用于计算奖励的宠物
    best_form_idx = -1        # 最高形态索引
    display_pet = None        # 用于展示的活跃宠物

    for p in all_pets:
        if p.is_active:
            display_pet = p
        if p.intimacy < 60:
            continue
        unlocked = json.loads(p.unlocked_forms) if isinstance(p.unlocked_forms, str) else p.unlocked_forms
        # 计算该宠物的最高形态索引
        form_idx = -1
        for f in FORM_ORDER:
            if f in unlocked:
                form_idx = max(form_idx, FORM_ORDER.index(f))
        # 分支进化（branch_xxx）视为最高阶（legend级）
        if any(uf.startswith("branch_") for uf in unlocked):
            form_idx = max(form_idx, 4)

        if form_idx > best_form_idx:
            best_form_idx = form_idx
            best_pet = p

    # 没有符合条件的宠物
    if not best_pet:
        if not display_pet:
            return {"triggered": False, "message": "还没有宠物呢～"}
        pet_name = FORM_NAMES.get(display_pet.pet_type, [None])[0] or display_pet.pet_type
        return {
            "triggered": False,
            "pet_name": pet_name,
            "pet_type": display_pet.pet_type,
            "pet_emoji": PET_EMOJI.get(display_pet.pet_type, {}).get(display_pet.current_form, "🐾"),
            "reward": None,
            "message": f"亲密度还不够（{display_pet.intimacy}/60），还不能出门冒险～",
            "passive_name": PASSIVE_SKILLS.get(display_pet.pet_type, {}).get("name", ""),
            "week_summary": _get_week_summary(cid, db),
        }

    # 使用最佳宠物的类型/亲密度计算奖励
    pet = best_pet
    pet_type = pet.pet_type
    display_type = display_pet.pet_type if display_pet else pet_type
    form_labels = FORM_NAMES.get(display_type, [])
    pet_emoji = PET_EMOJI.get(display_type, {}).get("legend" if best_form_idx >= 4 else FORM_ORDER[best_form_idx], "🐾")
    pet_name = form_labels[0] if form_labels else display_type

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


# ===== 游戏日志查看 =====


@router.get("/logs")
def get_game_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                  limit: int = 50, action_type: str = ""):
    """查看游戏行为日志"""
    cid = get_couple_id(user)
    from app.models.social import GameLog
    q = db.query(GameLog).filter(GameLog.couple_id == cid)
    if action_type:
        q = q.filter(GameLog.action_type == action_type)
    logs = q.order_by(GameLog.created_at.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "action_type": l.action_type,
        "item_id": l.item_id,
        "item_name": l.item_name,
        "details": l.details,
        "created_at": l.created_at.isoformat() if l.created_at else "",
    } for l in logs]


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
