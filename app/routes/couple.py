from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.user import User
from app.schemas.user import BindRequest, UserResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["情侣"])


# ===== 工具函数 =====

def has_partner(db: Session, user: User) -> bool:
    """检查用户是否已有真实的伴侣（个人 Couple 只有自己=无伴侣）"""
    if not user.couple_id:
        return False
    count = db.query(User).filter(User.couple_id == user.couple_id).count()
    return count >= 2


def get_partner_user(db: Session, user: User) -> User | None:
    """返回用户的伴侣，没有则返回 None"""
    if not user.couple_id:
        return None
    return (
        db.query(User)
        .filter(User.couple_id == user.couple_id, User.id != user.id)
        .first()
    )


# ===== 绑定伴侣 =====

@router.post("/bind")
def bind_partner(
    req: BindRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 自己是否已有伴侣
    if has_partner(db, user):
        raise HTTPException(400, "你已绑定伴侣，请先解绑再绑定其他人")

    # 对方是否存在
    partner = db.query(User).filter(User.invite_code == req.invite_code).first()
    if not partner:
        raise HTTPException(404, "邀请码无效")

    # 不能绑定自己
    if partner.id == user.id:
        raise HTTPException(400, "不能绑定自己")

    # 对方是否已有伴侣
    if has_partner(db, partner):
        raise HTTPException(400, "对方已绑定伴侣")

    # 创建共享 Couple
    shared = Couple(status="active")
    db.add(shared)
    db.flush()

    # 迁移两人个人数据到共享 Couple
    from app.models.plan import Plan, Wish
    from app.models.extra import Anniversary, Gift, ToDo
    from app.models.social import Level, LevelLog, Note, Task
    from app.models.card import Card

    DATA_MODELS = [Plan, Wish, Anniversary, Gift, ToDo, Level, LevelLog, Note, Task, Card]

    for cid in filter(None, {user.couple_id, partner.couple_id}):
        for model in DATA_MODELS:
            db.query(model).filter(model.couple_id == cid).update(
                {"couple_id": shared.id}
            )

    # 更新两人指向共享 Couple
    user.couple_id = shared.id
    partner.couple_id = shared.id
    db.commit()

    return {"ok": True, "couple_id": shared.id, "partner": partner.nickname}


# ===== 解绑伴侣 =====

@router.post("/unbind")
def unbind_partner(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not has_partner(db, user):
        raise HTTPException(400, "你没有绑定的伴侣")

    old_couple_id = user.couple_id
    members = db.query(User).filter(User.couple_id == old_couple_id).all()

    # 每人分到一个新的个人 Couple
    # 注意：数据不迁移，留在原共享 Couple 中（已归档）
    # 因为 plans/deliveries 没有 user_id，无法合理拆分给双方
    for member in members:
        personal = Couple(status="active")
        db.add(personal)
        db.flush()
        member.couple_id = personal.id

    # 归档旧 Couple
    old = db.query(Couple).filter(Couple.id == old_couple_id).first()
    if old:
        old.status = "archived"
        old.archived_at = datetime.now()

    db.commit()
    return {"ok": True, "message": "已解绑，双方各自拥有新的存钱空间"}


# ===== 获取伴侣信息 =====

@router.get("/partner", response_model=UserResponse | None)
def get_partner(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_partner_user(db, user)
