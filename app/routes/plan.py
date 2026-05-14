from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.plan import Delivery, Plan, Wish
from app.models.user import User
from app.schemas.plan import (
    DeliverRequest,
    DeliveryResponse,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    WishCreate,
    WishResponse,
    WishUpdate,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["存钱 & 心愿"])


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


# ===================== 存钱计划 =====================


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plans = db.query(Plan).filter(Plan.couple_id == cid).order_by(Plan.created_at.desc()).all()
    result = []
    for p in plans:
        deliveries = db.query(Delivery).filter(Delivery.plan_id == p.id).order_by(Delivery.created_at.desc()).all()
        result.append(PlanResponse(
            id=p.id, title=p.title, target_amount=p.target_amount,
            current_amount=p.current_amount, start_date=p.start_date,
            end_date=p.end_date, done=p.done, created_at=p.created_at,
            deliveries=[DeliveryResponse.model_validate(d) for d in deliveries],
        ))
    return result


@router.post("/plans")
def create_plan(
    req: PlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = Plan(
        couple_id=cid, title=req.title,
        target_amount=req.target_amount, start_date=req.start_date,
        end_date=req.end_date,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"ok": True, "plan_id": plan.id}


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    req: PlanUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    if req.title is not None:
        plan.title = req.title
    if req.target_amount is not None:
        plan.target_amount = req.target_amount
    if req.end_date is not None:
        plan.end_date = req.end_date
    db.commit()
    return {"ok": True}


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    db.query(Delivery).filter(Delivery.plan_id == plan_id).delete()
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.post("/plans/{plan_id}/deliver")
def deliver_plan(
    plan_id: int,
    req: DeliverRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    if plan.done:
        raise HTTPException(400, "计划已完成，不可继续交付")

    plan.current_amount += req.amount
    if plan.current_amount >= plan.target_amount:
        plan.done = True

    delivery = Delivery(plan_id=plan_id, amount=req.amount, note=req.note)
    db.add(delivery)
    db.commit()
    return {"ok": True, "current_amount": plan.current_amount, "done": plan.done}


# ===================== 心愿承诺 =====================


@router.get("/wishes", response_model=list[WishResponse])
def list_wishes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    wishes = db.query(Wish).filter(Wish.couple_id == cid).order_by(Wish.created_at.desc()).all()
    return wishes


@router.post("/wishes")
def create_wish(
    req: WishCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    wish = Wish(
        couple_id=cid, user_id=user.id,
        title=req.title, description=req.description, image_url=req.image_url,
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return {"ok": True, "wish_id": wish.id}


@router.put("/wishes/{wish_id}")
def update_wish(
    wish_id: int,
    req: WishUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    wish = db.query(Wish).filter(Wish.id == wish_id, Wish.couple_id == cid).first()
    if not wish:
        raise HTTPException(404, "心愿不存在")
    if req.status is not None:
        wish.status = req.status
    if req.description is not None:
        wish.description = req.description
    if req.image_url is not None:
        wish.image_url = req.image_url
    if req.fulfilled_date is not None:
        wish.fulfilled_date = req.fulfilled_date
    db.commit()
    return {"ok": True, "status": wish.status}


@router.delete("/wishes/{wish_id}")
def delete_wish(
    wish_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    wish = db.query(Wish).filter(Wish.id == wish_id, Wish.couple_id == cid).first()
    if not wish:
        raise HTTPException(404, "心愿不存在")
    db.delete(wish)
    db.commit()
    return {"ok": True}
