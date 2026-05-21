from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.checkin import Checkin
from app.models.couple import Couple
from app.models.user import User
from app.routes.social import add_exp as _add_exp
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/checkin", tags=["签到"])


@router.post("")
def do_checkin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """自动签到：每天第一次打开时调用"""
    if not user.couple_id:
        return {"ok": True, "message": "未绑定伴侣", "checked": False}

    today = date.today()
    # 今天是否已签
    existing = db.query(Checkin).filter(
        Checkin.couple_id == user.couple_id,
        Checkin.user_id == user.id,
        Checkin.checkin_date == today,
    ).first()
    if existing:
        return {"ok": True, "checked": False, "message": "今日已签到"}

    # 签到
    db.add(Checkin(couple_id=user.couple_id, user_id=user.id, checkin_date=today))

    # 签到奖励
    couple = db.query(Couple).filter(Couple.id == user.couple_id).first()
    bonus_msg = ""
    if couple:
        # 基础奖励：+5 积分
        couple.shards = (couple.shards or 0) + 5

        # 伴侣双签奖励：如果伴侣今天已经签了，再+5
        partner = db.query(User).filter(
            User.couple_id == user.couple_id, User.id != user.id
        ).first()
        if partner:
            partner_checked = db.query(Checkin).filter(
                Checkin.couple_id == user.couple_id,
                Checkin.user_id == partner.id,
                Checkin.checkin_date == today,
            ).first() is not None
            if partner_checked:
                couple.shards = (couple.shards or 0) + 5
                bonus_msg = " 伴侣已签到，获得双签奖励+5💎"

    # 签到经验奖励
    _add_exp(user.couple_id, 5, f"每日签到", db)

    # 更新火花状态
    _update_spark(user.couple_id, today, db)

    return {
        "ok": True,
        "checked": True,
        "message": f"签到成功🔥 +5💎 +5EXP{bonus_msg}",
    }


@router.get("/status")
def get_checkin_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取签到和火花状态"""
    if not user.couple_id:
        return {"spark_count": 0, "max_spark_count": 0, "spark_status": "active", "checked_today": False}

    today = date.today()
    couple = db.query(Couple).filter(Couple.id == user.couple_id).first()
    if not couple:
        return {"spark_count": 0, "max_spark_count": 0, "spark_status": "active", "checked_today": False}

    # 检查签到
    my_checkin = db.query(Checkin).filter(
        Checkin.couple_id == user.couple_id,
        Checkin.user_id == user.id,
        Checkin.checkin_date == today,
    ).first()

    # 获取伴侣签到状态
    partner = db.query(User).filter(
        User.couple_id == user.couple_id, User.id != user.id
    ).first()
    partner_checked = False
    if partner:
        partner_checked = db.query(Checkin).filter(
            Checkin.couple_id == user.couple_id,
            Checkin.user_id == partner.id,
            Checkin.checkin_date == today,
        ).first() is not None

    return {
        "spark_count": couple.spark_count or 0,
        "max_spark_count": couple.max_spark_count or 0,
        "spark_status": couple.spark_status or "active",
        "checked_today": my_checkin is not None,
        "partner_checked_today": partner_checked,
        "today_continuous_days": _calc_continuous(couple.id, today, db),
    }


@router.get("/spark")
def get_spark(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取火花状态"""
    if not user.couple_id:
        return {"spark_count": 0, "max_spark_count": 0, "spark_status": "active"}

    today = date.today()
    _update_spark(user.couple_id, today, db)

    couple = db.query(Couple).filter(Couple.id == user.couple_id).first()
    return {
        "spark_count": couple.spark_count or 0,
        "max_spark_count": couple.max_spark_count or 0,
        "spark_status": couple.spark_status or "active",
        "streak_days": _calc_continuous(couple.id, today, db),
    }


# ===== 火花核心逻辑 =====


def _update_spark(couple_id: int, today: date, db: Session):
    """每日检查并更新火花状态"""
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if not couple:
        return

    yesterday = today - timedelta(days=1)

    yesterday_count = db.query(Checkin).filter(
        Checkin.couple_id == couple_id,
        Checkin.checkin_date == yesterday,
    ).count()

    today_count = db.query(Checkin).filter(
        Checkin.couple_id == couple_id,
        Checkin.checkin_date == today,
    ).count()

    if yesterday_count == 0:
        couple.spark_status = "gray"

    if couple.spark_status == "gray":
        three_days_count = db.query(Checkin).filter(
            Checkin.couple_id == couple_id,
            Checkin.checkin_date >= today - timedelta(days=3),
            Checkin.checkin_date <= today,
        ).count()

        if three_days_count >= 3:
            couple.spark_status = "active"
        else:
            oldest_in_window = db.query(Checkin.checkin_date).filter(
                Checkin.couple_id == couple_id,
                Checkin.checkin_date >= today - timedelta(days=6),
            ).order_by(Checkin.checkin_date).first()

            if oldest_in_window and (today - oldest_in_window[0]).days >= 3:
                if (couple.spark_count or 0) > (couple.max_spark_count or 0):
                    couple.max_spark_count = couple.spark_count
                couple.spark_count = 0
                couple.spark_status = "active"

    if couple.spark_status == "active":
        continuous = _calc_continuous(couple_id, today, db)
        couple.spark_count = continuous

    db.commit()


def _calc_continuous(couple_id: int, today: date, db: Session) -> int:
    """计算截至今天的连续签到天数（两人中任意一人签到就算一天）"""
    days = 0
    d = today
    while True:
        count = db.query(Checkin).filter(
            Checkin.couple_id == couple_id,
            Checkin.checkin_date == d,
        ).count()
        if count == 0:
            break
        days += 1
        d -= timedelta(days=1)
    return days
