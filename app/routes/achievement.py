from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.achievements import ACHIEVEMENTS
from app.database import get_db
from app.models.achievement import AchievementProgress
from app.models.couple import Couple
from app.models.pet import Pet, Inventory
from app.models.plan import Delivery, Plan
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/achievements", tags=["成就"])


def _init_achievements(couple_id: int, db: Session):
    """确保该 couple 有所有成就的进度记录"""
    existing = {a.achievement_id for a in db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == couple_id
    ).all()}
    for aid in ACHIEVEMENTS:
        if aid not in existing:
            db.add(AchievementProgress(
                couple_id=couple_id,
                achievement_id=aid,
            ))
    db.commit()


def _unlock_achievement(couple_id: int, achievement_id: str, db: Session):
    """解锁成就并发放奖励"""
    prog = db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == couple_id,
        AchievementProgress.achievement_id == achievement_id,
    ).first()
    if not prog:
        prog = AchievementProgress(
            couple_id=couple_id,
            achievement_id=achievement_id,
        )
        db.add(prog)
        db.flush()
    if prog.unlocked:
        return False  # 已解锁

    prog.unlocked = True
    prog.unlocked_at = datetime.now()
    prog.claimed = False

    cfg = ACHIEVEMENTS.get(achievement_id)
    if cfg:
        couple = db.query(Couple).filter(Couple.id == couple_id).first()
        if couple:
            if cfg["reward_type"] == "shards":
                couple.shards = (couple.shards or 0) + cfg["reward_amount"]
            elif cfg["reward_type"] == "tickets":
                couple.draw_tickets = (couple.draw_tickets or 0) + cfg["reward_amount"]
    db.commit()
    return True


def check_and_unlock(couple_id: int, db: Session):
    """检查所有成就可以否解锁"""
    _init_achievements(couple_id, db)
    unlocked_any = False

    # 已解锁的成就ID
    unlocked_ids = {a.achievement_id for a in db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == couple_id,
        AchievementProgress.unlocked == True,
    ).all()}

    # 收集统计数据
    from app.models.checkin import Checkin
    from datetime import date, timedelta
    today = date.today()

    # 连续签到天数
    continuous = 0
    d = today
    while True:
        c = db.query(Checkin).filter(
            Checkin.couple_id == couple_id,
            Checkin.checkin_date == d,
        ).count()
        if c == 0:
            break
        continuous += 1
        d -= timedelta(days=1)

    # 累计存款
    total_delivered = sum(
        d[0] or 0 for d in
        db.query(Delivery).join(Plan, Delivery.plan_id == Plan.id)
        .filter(Plan.couple_id == couple_id).with_entities(Delivery.amount).all()
    )

    # 宠物数量
    pet_count = db.query(Pet).filter(Pet.couple_id == couple_id).count()

    # 所有宠物类型
    pet_types = {p.pet_type for p in db.query(Pet).filter(Pet.couple_id == couple_id).all()}

    # 所有已解锁形态数
    total_forms = 0
    max_intimacy = False
    for p in db.query(Pet).filter(Pet.couple_id == couple_id).all():
        import json
        forms = json.loads(p.unlocked_forms) if isinstance(p.unlocked_forms, str) else p.unlocked_forms
        total_forms += len(forms)
        if p.intimacy and p.intimacy >= 100:
            max_intimacy = True

    # 抽卡次数（从inventory抽到的物品总数 - 粗略估算）
    gacha_item_count = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
    ).count()

    gacha_ssr = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type.in_(["evolution_item"]),
        Inventory.item_id.in_(["mech_core", "stardust"]),
    ).count()

    gacha_ssrp = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "consumable",
        Inventory.item_id == "forgive_me",
    ).count() + db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "consumable",
        Inventory.item_id == "serve_me",
    ).count()

    # 逐一检查
    checks = {
        "streak_7": continuous >= 7,
        "streak_14": continuous >= 14,
        "streak_21": continuous >= 21,
        "streak_30": continuous >= 30,
        "streak_60": continuous >= 60,
        "streak_100": continuous >= 100,
        "saving_100": total_delivered >= 100,
        "saving_1000": total_delivered >= 1000,
        "saving_5000": total_delivered >= 5000,
        "saving_20000": total_delivered >= 20000,
        "saving_100000": total_delivered >= 100000,
        "first_pet": pet_count >= 1,
        "first_form": total_forms >= 2,  # baby + 至少1个新形态
        "max_intimacy": max_intimacy,
        "all_pets": len(pet_types) >= 5,
        "gacha_10": gacha_item_count >= 10,
        "gacha_100": gacha_item_count >= 100,
        "gacha_1000": gacha_item_count >= 1000,
        "first_ssr": gacha_ssr >= 1,
        "first_ssrp": gacha_ssrp >= 1,
        "all_pets_collected": len(pet_types) >= 5,
        "first_bind": True,  # 能在couple里说明已绑定（有伴侣）
        "first_evolve": total_forms > len(pet_types),  # 有分支形态
    }

    for aid, condition in checks.items():
        if aid not in unlocked_ids and condition:
            if _unlock_achievement(couple_id, aid, db):
                unlocked_any = True

    return unlocked_any


@router.get("")
def get_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有成就及完成状态"""
    if not user.couple_id:
        return {"achievements": [], "total": 0, "unlocked": 0}

    check_and_unlock(user.couple_id, db)

    records = db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == user.couple_id,
    ).all()
    record_map = {r.achievement_id: r for r in records}

    result = []
    for aid, cfg in ACHIEVEMENTS.items():
        prog = record_map.get(aid)
        result.append({
            "id": aid,
            "name": cfg["name"],
            "desc": cfg["desc"],
            "category": cfg["category"],
            "hidden": cfg["hidden"],
            "reward_type": cfg["reward_type"],
            "reward_amount": cfg["reward_amount"],
            "unlocked": prog.unlocked if prog else False,
            "unlocked_at": prog.unlocked_at.isoformat() if prog and prog.unlocked_at else None,
            "claimed": prog.claimed if prog else False,
        })

    unlocked_count = sum(1 for r in result if r["unlocked"])
    return {
        "achievements": result,
        "total": len(result),
        "unlocked": unlocked_count,
    }


@router.post("/check")
def check_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """手动检查成就可以否解锁"""
    if not user.couple_id:
        return {"unlocked": []}
    check_and_unlock(user.couple_id, db)
    records = db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == user.couple_id,
        AchievementProgress.unlocked == True,
        AchievementProgress.claimed == False,
    ).all()
    return {
        "new_unlocked": [
            {
                "id": r.achievement_id,
                "name": ACHIEVEMENTS.get(r.achievement_id, {}).get("name", r.achievement_id),
            }
            for r in records
        ],
    }
