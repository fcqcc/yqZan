import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.couple import Couple
from app.models.pet import Pet
from app.models.pet import EXP_PER_LEVEL, MAX_LEVEL, get_form_by_level
from app.routes.pet import add_exp_to_active_pet
from app.models.plan import Delivery, Plan, Wish
from app.models.user import User
from app.routes.social import add_exp as _add_exp
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


def get_couple_id_or_none(user: User) -> int | None:
    return user.couple_id

def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def calc_remaining_days(end_date: str) -> int | None:
    if not end_date:
        return None
    try:
        end = date.fromisoformat(end_date)
        delta = (end - date.today()).days
        return max(delta, 0)
    except ValueError:
        return None


def build_plan_response(plan: Plan, db: Session) -> PlanResponse:
    deliveries = db.query(Delivery).filter(Delivery.plan_id == plan.id).order_by(Delivery.created_at.desc()).all()
    remaining = None if plan.unlimited else calc_remaining_days(plan.end_date)
    return PlanResponse(
        id=plan.id,
        title=plan.title,
        target_amount=plan.target_amount,
        current_amount=plan.current_amount,
        start_date=plan.start_date,
        end_date=plan.end_date,
        unlimited=plan.unlimited,
        done=plan.done,
        notify_status=plan.notify_status or "",
        remaining_days=remaining,
        created_at=plan.created_at,
        deliveries=[DeliveryResponse.model_validate(d) for d in deliveries],
    )


# ===================== 存钱计划 =====================


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    plans = db.query(Plan).filter(Plan.couple_id == cid).order_by(Plan.created_at.desc()).all()
    return [build_plan_response(p, db) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    return build_plan_response(plan, db)


@router.post("/plans")
def create_plan(
    req: PlanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    plan = Plan(
        couple_id=cid, title=req.title,
        target_amount=req.target_amount,
        start_date=req.start_date,
        end_date=req.end_date,
        unlimited=req.unlimited,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"ok": True, "plan_id": plan.id}


@router.post("/plans/{plan_id}/deliver")
def deliver_plan(
    plan_id: int,
    req: DeliverRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """存钱交付，自动检测完成并设置通知状态"""
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    if plan.done:
        raise HTTPException(400, "计划已完成")

    plan.current_amount += req.amount
    db.add(Delivery(plan_id=plan_id, amount=req.amount, note=req.note))

    couple = db.query(Couple).filter(Couple.id == cid).first()

    # 💎 存钱奖励积分（每笔+2）
    if couple:
        couple.shards = (couple.shards or 0) + 2

    # ⭐ 存钱奖励经验（每笔+3）
    _add_exp(cid, 3, f"存钱：{plan.title}", db)

    # 🫶 喂食当前活跃宠物（亲密+3）
    active_pet = db.query(Pet).filter(
        Pet.couple_id == cid, Pet.is_active == True
    ).first()
    if active_pet:
        from datetime import timedelta
        now = datetime.now()
        if not active_pet.last_fed_at or (now - active_pet.last_fed_at) >= timedelta(seconds=30):
            active_pet.intimacy = min(100, active_pet.intimacy + 3)
            active_pet.last_fed_at = now

    # 🐾 存款宠物经验（按次数，每日上限3次）
    if couple:
        today = date.today()
        if couple.deposit_exp_date != today:
            couple.deposit_exp_date = today
            couple.deposit_exp_count = 0
        if couple.deposit_exp_count < 3:
            couple.deposit_exp_count += 1
            add_exp_to_active_pet(cid, 1, db)

    # 🎟️ 存钱奖励抽卡券（每日上限 4 张）
    today = datetime.now().date()
    today_count = (
        db.query(Delivery)
        .join(Plan, Delivery.plan_id == Plan.id)
        .filter(
            Plan.couple_id == cid,
            Delivery.created_at >= today.strftime("%Y-%m-%d"),
        )
        .count()
    )
    if today_count <= 4:
        if couple:
            couple.draw_tickets = (couple.draw_tickets or 0) + 1

    # 检测是否达成目标
    if plan.current_amount >= plan.target_amount:
        plan.done = True
        # 设置通知：自己已读，对方未读
        notify = {str(user.id): "read"}
        # 找伴侣
        partner = db.query(User).filter(
            User.couple_id == cid, User.id != user.id
        ).first()
        if partner:
            notify[str(partner.id)] = "unread"
        plan.notify_status = json.dumps(notify, ensure_ascii=False)
        # 🎟️ 目标达成奖励 10 张
        couple = db.query(Couple).filter(Couple.id == cid).first()
        if couple:
            couple.draw_tickets = (couple.draw_tickets or 0) + 10

        # 🐾 目标达成宠物经验（按次数，每日上限2次）
        if couple:
            today = date.today()
            if couple.goal_exp_date != today:
                couple.goal_exp_date = today
                couple.goal_exp_count = 0
            if couple.goal_exp_count < 2:
                couple.goal_exp_count += 1
                add_exp_to_active_pet(cid, 1, db)

    db.commit()
    return {"ok": True, "current_amount": plan.current_amount, "done": plan.done}


@router.post("/plans/{plan_id}/congratulate")
def congratulate_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记计划完成的祝贺通知为已读"""
    cid = get_couple_id(user)
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.couple_id == cid).first()
    if not plan:
        raise HTTPException(404, "计划不存在")
    if not plan.done:
        raise HTTPException(400, "计划尚未完成")

    # 更新当前用户的通知状态为已读
    notify = {}
    if plan.notify_status:
        try:
            notify = json.loads(plan.notify_status)
        except json.JSONDecodeError:
            notify = {}
    notify[str(user.id)] = "read"
    plan.notify_status = json.dumps(notify, ensure_ascii=False)
    db.commit()
    return {"ok": True}


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
    db.delete(plan)
    db.commit()
    return {"ok": True}
