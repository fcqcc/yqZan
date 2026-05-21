from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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

    # 签到次数（累计点击次数）
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

    # 总签到天数
    total_checkins = db.query(Checkin).filter(
        Checkin.couple_id == couple_id,
    ).count()

    # 累计存款
    total_delivered = sum(
        d[0] or 0 for d in
        db.query(Delivery).join(Plan, Delivery.plan_id == Plan.id)
        .filter(Plan.couple_id == couple_id).with_entities(Delivery.amount).all()
    )

    # 已完成的目标数
    done_plans = db.query(Plan).filter(
        Plan.couple_id == couple_id,
        Plan.done == True,
    ).count()

    # 宠物数量 + 所有宠物亲密度检查
    pet_count = db.query(Pet).filter(Pet.couple_id == couple_id).count()
    pet_types = {p.pet_type for p in db.query(Pet).filter(Pet.couple_id == couple_id).all()}
    all_pets_60 = True
    all_pets = db.query(Pet).filter(Pet.couple_id == couple_id).all()
    for p in all_pets:
        if (p.intimacy or 0) < 60:
            all_pets_60 = False
            break

    # 所有已解锁形态 + 检测传说形态
    total_forms = 0
    max_intimacy = False
    has_legend = False
    for p in db.query(Pet).filter(Pet.couple_id == couple_id).all():
        import json
        forms = json.loads(p.unlocked_forms) if isinstance(p.unlocked_forms, str) else p.unlocked_forms
        total_forms += len(forms)
        if p.intimacy and p.intimacy >= 100:
            max_intimacy = True
        if "legend" in forms or any(f.startswith("branch_") and "legend" in f for f in forms):
            has_legend = True

    # 抽卡次数
    gacha_item_count = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
    ).count()

    # 抽到SSR宠物（star_fox / bamboo_dragon / wave_cat / honey_bear）
    has_golden = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "pet",
        Inventory.item_id.in_(["star_fox", "bamboo_dragon", "wave_cat", "honey_bear"]),
    ).count() > 0 or db.query(Pet).filter(
        Pet.couple_id == couple_id,
        Pet.pet_type.in_(["star_fox", "bamboo_dragon", "wave_cat", "honey_bear"]),
    ).count() > 0

    gacha_ssrp = db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "consumable",
        Inventory.item_id == "forgive_me",
    ).count() + db.query(Inventory).filter(
        Inventory.couple_id == couple_id,
        Inventory.item_type == "consumable",
        Inventory.item_id == "serve_me",
    ).count()

    # 等级检查
    from app.models.social import Level as LvlModel
    lvl_record = db.query(LvlModel).filter(LvlModel.couple_id == couple_id).first()
    current_level = lvl_record.level if lvl_record else 1

    # 火花状态检查
    spark_count = db.query(Couple).filter(Couple.id == couple_id).first()
    spark_val = spark_count.spark_count if spark_count else 0
    spark_status = spark_count.spark_status if spark_count else "active"

    # 逐一检查
    checks = {
        "streak_3": continuous >= 3,
        "streak_5": continuous >= 5,
        "streak_7": continuous >= 7,
        "streak_10": continuous >= 10,
        "streak_14": continuous >= 14,
        "streak_21": continuous >= 21,
        "streak_30": continuous >= 30,
        "streak_45": continuous >= 45,
        "streak_60": continuous >= 60,
        "streak_100": continuous >= 100,
        "first_open": total_checkins >= 1,
        "first_deposit": total_delivered >= 1,
        "first_goal": done_plans >= 1,
        "first_bind": True,
        "first_pet": pet_count >= 1,
        "first_form": total_forms >= 2,
        "first_evolve": total_forms > len(pet_types),
        "legend_form": has_legend,
        "max_intimacy": max_intimacy,
        "all_pets": len(pet_types) >= 5,
        "gacha_10": gacha_item_count >= 10,
        "gacha_100": gacha_item_count >= 100,
        "gacha_1000": gacha_item_count >= 1000,
        "golden_legend": has_golden,
        "first_ssrp": gacha_ssrp >= 1,
        "all_pets_collected": len(pet_types) >= 5,
        "streak_recover": False,
        # 新增
        "all_pets_intimacy_60": pet_count >= 1 and all_pets_60,
        "level_10": current_level >= 10,
        "level_30": current_level >= 30,
        "spark_7": spark_val >= 7 and spark_status == "active",
        "spark_30": spark_val >= 30 and spark_status == "active",
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


@router.post("/{achievement_id}/claim")
def claim_achievement(achievement_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """标记成就已领取（弹窗关闭后不再展示）"""
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    prog = db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == user.couple_id,
        AchievementProgress.achievement_id == achievement_id,
    ).first()
    if not prog:
        raise HTTPException(404, "成就记录不存在")
    if not prog.unlocked:
        raise HTTPException(400, "该成就尚未解锁")
    prog.claimed = True
    prog.claimed_at = datetime.now()
    db.commit()
    return {"ok": True}


@router.post("/claim-all")
def claim_all_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """标记所有未领取的成就为已领取"""
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    now = datetime.now()
    count = db.query(AchievementProgress).filter(
        AchievementProgress.couple_id == user.couple_id,
        AchievementProgress.unlocked == True,
        AchievementProgress.claimed == False,
    ).update({"claimed": True, "claimed_at": now})
    db.commit()
    return {"ok": True, "claimed_count": count}


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
