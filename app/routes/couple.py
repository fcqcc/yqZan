from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.user import User
from app.schemas.user import BindRequest, UserResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["情侣"])

# ===== 数据迁移工具 =====

COUPLE_DATA_MODELS = None  # lazy import

def get_couple_data_models():
    """懒加载所有包含 couple_id 的模型"""
    global COUPLE_DATA_MODELS
    if COUPLE_DATA_MODELS is None:
        from app.models.plan import Plan, Wish
        from app.models.extra import Anniversary, Gift, ToDo
        from app.models.social import Level, LevelLog, Note, Task
        from app.models.card import Card
        COUPLE_DATA_MODELS = [Plan, Wish, Anniversary, Gift, ToDo, Level, LevelLog, Note, Task, Card]
    return COUPLE_DATA_MODELS


def migrate_couple_data(db: Session, old_couple_id: int, new_couple_id: int):
    """将 old_couple 下的所有数据迁移到 new_couple"""
    for model in get_couple_data_models():
        db.query(model).filter(model.couple_id == old_couple_id).update(
            {"couple_id": new_couple_id}
        )


def create_personal_couple(db: Session) -> Couple:
    """创建个人 Couple"""
    couple = Couple(status="active")
    db.add(couple)
    db.flush()
    return couple


# ===== 绑定伴侣 =====

@router.post("/bind")
def bind_partner(
    req: BindRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    partner = db.query(User).filter(User.invite_code == req.invite_code).first()
    if not partner:
        raise HTTPException(404, "邀请码无效")
    if partner.id == user.id:
        raise HTTPException(400, "不能绑定自己")
    if partner.couple_id:
        # 检查对方是否已有伴侣（couple 里有 2 人）
        partner_count = db.query(User).filter(User.couple_id == partner.couple_id).count()
        if partner_count >= 2:
            raise HTTPException(400, "对方已绑定伴侣")

    # 创建共享 Couple
    shared = Couple(status="active")
    db.add(shared)
    db.flush()

    # 迁移用户数据到共享 Couple
    old_user_cid = user.couple_id
    old_partner_cid = partner.couple_id

    if old_user_cid:
        migrate_couple_data(db, old_user_cid, shared.id)
    if old_partner_cid and old_partner_cid != old_user_cid:
        migrate_couple_data(db, old_partner_cid, shared.id)

    # 更新两人 couple_id
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
    if not user.couple_id:
        raise HTTPException(400, "你还没有绑定")

    # 检查是否真的有伴侣
    members = db.query(User).filter(User.couple_id == user.couple_id).all()
    if len(members) < 2:
        raise HTTPException(400, "你没有绑定的伴侣")

    old_couple_id = user.couple_id

    # 每人分到一个新的个人 Couple
    for member in members:
        personal = create_personal_couple(db)
        migrate_couple_data(db, old_couple_id, personal.id)
        member.couple_id = personal.id

    # 归档旧 Couple
    old = db.query(Couple).filter(Couple.id == old_couple_id).first()
    if old:
        old.status = "archived"
        old.archived_at = datetime.now()

    db.commit()
    return {"ok": True, "message": "已解绑，数据已拆分"}


# ===== 获取伴侣信息 =====

@router.get("/partner", response_model=UserResponse | None)
def get_partner(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.couple_id:
        return None
    partner = (
        db.query(User)
        .filter(User.couple_id == user.couple_id, User.id != user.id)
        .first()
    )
    return partner
