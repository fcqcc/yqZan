from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.user import User
from app.schemas.user import BindRequest, UserResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["情侣"])


@router.post("/bind")
def bind_partner(
    req: BindRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.couple_id:
        raise HTTPException(400, "你已绑定伴侣")

    partner = db.query(User).filter(User.invite_code == req.invite_code).first()
    if not partner:
        raise HTTPException(404, "邀请码无效")
    if partner.id == user.id:
        raise HTTPException(400, "不能绑定自己")
    if partner.couple_id:
        raise HTTPException(400, "对方已绑定伴侣")

    couple = Couple(status="active")
    db.add(couple)
    db.flush()

    user.couple_id = couple.id
    partner.couple_id = couple.id
    db.commit()

    return {"ok": True, "couple_id": couple.id, "partner": partner.nickname}


@router.post("/unbind")
def unbind_partner(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.couple_id:
        raise HTTPException(400, "你还没有绑定")

    couple = db.query(Couple).filter(Couple.id == user.couple_id).first()
    if not couple:
        raise HTTPException(404, "情侣空间不存在")

    couple.status = "archived"
    couple.archived_at = datetime.now()

    members = db.query(User).filter(User.couple_id == couple.id).all()
    for member in members:
        member.couple_id = None

    db.commit()
    return {"ok": True, "message": "已解绑，数据已归档"}


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
