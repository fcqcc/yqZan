from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card_task import CardTask
from app.models.couple import Couple
from app.models.pet import Inventory
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/card-tasks", tags=["卡片任务"])


# ===== 卡片展示名称映射 =====

CARD_NAMES = {
    "chore_dishes":  "洗碗🧹",
    "chore_mop":     "拖地🧹",
    "chore_cook":    "做饭🍳",
    "chore_laundry": "洗衣🧺",
    "chore_garbage": "倒垃圾🗑️",
    "serve_me":      "为我服务👑",
    "forgive_me":    "原谅我吧🥺",
    "decline_card":  "我不要😤",
}

ACTIVE_STATUSES = ("pending", "completed_pending", "disputed")


def get_partner(user: User, db: Session) -> User:
    """获取伴侣"""
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    partner = db.query(User).filter(
        User.couple_id == user.couple_id, User.id != user.id
    ).first()
    if not partner:
        raise HTTPException(400, "伴侣不存在")
    return partner


def check_conflict(couple_id: int, card_item_id: str, db: Session):
    """检查同类型卡片是否还在执行中"""
    existing = db.query(CardTask).filter(
        CardTask.couple_id == couple_id,
        CardTask.card_item_id == card_item_id,
        CardTask.status.in_(ACTIVE_STATUSES),
    ).first()
    if existing:
        assigner = db.query(User).filter(User.id == existing.assigner_id).first()
        name = assigner.nickname if assigner else "对方"
        raise HTTPException(409, f"同类型任务正在执行中（由 {name} 发起），请等待完成后再试")


def build_task_response(task: CardTask, current_user: User, db: Session):
    """构建任务响应"""
    assigner = db.query(User).filter(User.id == task.assigner_id).first()
    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    is_assigner = task.assigner_id == current_user.id

    # 显示文本
    task_display_text = ""
    if task.card_item_id == "serve_me":
        if is_assigner:
            if task.status == "completed":
                task_display_text = f"对方已完成服务✅ 快享受吧！👑"
            elif task.status == "completed_pending":
                task_display_text = "对方声称已完成，确认一下？"
            else:
                task_display_text = f"等待{assignee.nickname if assignee else '对方'}为你服务…👑"
        else:
            if task.status == "completed":
                task_display_text = "你已完成服务 ✅"
            elif task.status == "completed_pending":
                task_display_text = f"已声明完成，等待{assigner.nickname if assigner else '对方'}确认"
            else:
                task_display_text = f"对方对你使用了「为我服务」👑 马上去服务TA！"
    elif task.card_item_id == "forgive_me":
        if is_assigner:
            if task.status == "completed":
                task_display_text = "对方原谅你了 💕"
            elif task.rejected:
                task_display_text = "对方暂时不原谅你，是否再次请求？🥺"
            else:
                task_display_text = "等待对方的原谅…"
        else:
            if task.status == "completed":
                task_display_text = "你已原谅了对方 💕"
            elif task.status == "completed_pending":
                task_display_text = "你已原谅了对方，等待TA确认…"
            elif task.rejected:
                task_display_text = "你暂时不想原谅TA，等待TA再次请求…"
            else:
                task_display_text = "对方对你使用了极其稀有的原谅卡🤲 求求你，可以原谅他吗？"

    return {
        "id": task.id,
        "card_item_id": task.card_item_id,
        "card_name": task.card_name,
        "assigner_id": task.assigner_id,
        "assigner_name": assigner.nickname if assigner else "对方",
        "assignee_id": task.assignee_id,
        "assignee_name": assignee.nickname if assignee else "对方",
        "status": task.status,
        "my_role": "assigner" if is_assigner else "assignee",
        "rejected": bool(task.rejected) if hasattr(task, 'rejected') else False,
        "task_display_text": task_display_text,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.post("/use")
def use_card(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """使用卡片 → 创建任务"""
    cid = user.couple_id
    if not cid:
        raise HTTPException(400, "未绑定伴侣")

    inventory_id = req.get("inventory_id")
    if not inventory_id:
        raise HTTPException(400, "缺少 inventory_id")

    # 查背包
    inv = db.query(Inventory).filter(
        Inventory.id == inventory_id,
        Inventory.couple_id == cid,
        Inventory.quantity > 0,
    ).first()
    if not inv:
        raise HTTPException(404, "物品不存在")

    item_id = inv.item_id
    if item_id not in CARD_NAMES:
        raise HTTPException(400, "该物品不是可使用的任务卡片")

    # 为我服务卡 → 创建任务（接收方不得拒绝）
    if item_id == "serve_me":
        check_conflict(cid, item_id, db)
        inv.quantity -= 1
        partner = get_partner(user, db)
        card_name = CARD_NAMES[item_id]
        task = CardTask(
            couple_id=cid,
            card_item_id=item_id,
            card_name=card_name,
            assigner_id=user.id,
            assignee_id=partner.id,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        from app.routes.pet import _log_game_action
        _log_game_action(cid, "card_use", item_id,
                         f"使用{card_name}：命令{partner.nickname if partner else '对方'}服务",
                         db, item_name=card_name)
        return {
            "ok": True,
            "effect": f"你命令{partner.nickname}为你服务，不得拒绝！👑",
            "super_rare": True,
            "card_task": build_task_response(task, user, db),
        }
    if item_id == "forgive_me":
        check_conflict(cid, item_id, db)
        inv.quantity -= 1
        partner = get_partner(user, db)
        card_name = CARD_NAMES[item_id]
        task = CardTask(
            couple_id=cid,
            card_item_id=item_id,
            card_name=card_name,
            assigner_id=user.id,
            assignee_id=partner.id,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        from app.routes.pet import _log_game_action
        _log_game_action(cid, "card_use", item_id,
                         f"使用{card_name}：等待{partner.nickname if partner else '对方'}原谅",
                         db, item_name=card_name)
        return {
            "ok": True,
            "effect": f"你使用了「{card_name}」，等待{partner.nickname}的原谅中…",
            "card_task": build_task_response(task, user, db),
        }
    if item_id == "decline_card":
        raise HTTPException(400, "我不要卡不能主动使用，请在首页任务区收到指派时使用此卡拒绝")

    # 剩下是家务卡 → 需要任务流程
    # 检查冲突
    check_conflict(cid, item_id, db)

    partner = get_partner(user, db)
    card_name = CARD_NAMES[item_id]

    # 消耗背包
    inv.quantity -= 1

    # 创建任务
    task = CardTask(
        couple_id=cid,
        card_item_id=item_id,
        card_name=card_name,
        assigner_id=user.id,
        assignee_id=partner.id,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    from app.routes.pet import _log_game_action
    _log_game_action(cid, "card_use", item_id,
                     f"使用{card_name}：指派{partner.nickname if partner else '对方'}去做",
                     db, item_name=card_name)

    return {
        "ok": True,
        "effect": f"指派了{partner.nickname}去{card_name}，等待对方确认中",
        "card_task": build_task_response(task, user, db),
    }


@router.get("/active")
def get_active_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前活跃的卡片任务（双方各自视角所需的信息）"""
    cid = user.couple_id
    if not cid:
        return {"as_assigner": [], "as_assignee": []}

    tasks = db.query(CardTask).filter(
        CardTask.couple_id == cid,
        CardTask.status.in_(ACTIVE_STATUSES),
    ).order_by(CardTask.created_at.desc()).all()

    # 也查询近期已完成的任务（5分钟内），让发起方看到结果
    from datetime import timedelta
    recent_cutoff = datetime.now() - timedelta(minutes=5)
    recent_completed = db.query(CardTask).filter(
        CardTask.couple_id == cid,
        CardTask.status == "completed",
        CardTask.updated_at >= recent_cutoff,
    ).order_by(CardTask.updated_at.desc()).all()

    as_assigner = []
    as_assignee = []
    for t in tasks:
        resp = build_task_response(t, user, db)
        if t.assigner_id == user.id:
            as_assigner.append(resp)
        if t.assignee_id == user.id:
            as_assignee.append(resp)
    for t in recent_completed:
        resp = build_task_response(t, user, db)
        if t.assigner_id == user.id:
            as_assigner.append(resp)
        if t.assignee_id == user.id:
            as_assignee.append(resp)

    return {
        "as_assigner": as_assigner,
        "as_assignee": as_assignee,
    }


@router.post("/{task_id}/complete")
def complete_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """接收方：已完成"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assignee_id != user.id:
        raise HTTPException(403, "只有接收方可以声明完成")
    if task.status != "pending" and task.status != "disputed":
        raise HTTPException(400, f"当前状态({task.status})不能声明完成")

    task.status = "completed_pending"
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db)}


@router.post("/{task_id}/decline")
def decline_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """接收方：我不要卡"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assignee_id != user.id:
        raise HTTPException(403, "只有接收方可以使用」我不要卡「")
    if task.status != "pending":
        raise HTTPException(400, f"当前状态({task.status})不能使用」我不要卡「")
    if task.card_item_id == "serve_me":
        raise HTTPException(400, "「为我服务卡」无法拒绝！👑")
    if task.card_item_id == "forgive_me":
        raise HTTPException(400, "原谅卡不能使用「我不要卡」，请使用「好的」或「我不要」按钮")

    # 消耗对方的"我不要卡"（检查背包）
    decline_inv = db.query(Inventory).filter(
        Inventory.couple_id == task.couple_id,
        Inventory.item_type == "consumable",
        Inventory.item_id == "decline_card",
        Inventory.quantity > 0,
    ).first()
    if not decline_inv:
        raise HTTPException(400, "你背包中没有「我不要卡」，无法拒绝任务")

    decline_inv.quantity -= 1
    task.status = "declined"
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db)}


@router.post("/{task_id}/confirm")
def confirm_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发起方：确认完成"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assigner_id != user.id:
        raise HTTPException(403, "只有发起方可以确认完成")
    if task.status != "completed_pending":
        raise HTTPException(400, f"当前状态({task.status})不能确认完成")

    task.status = "completed"
    db.commit()
    msg = "你们和解了 💕" if task.card_item_id == "forgive_me" else "任务已完成✅"
    return {"ok": True, "card_task": build_task_response(task, user, db), "message": msg}


@router.post("/{task_id}/dispute")
def dispute_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发起方：未完成（退回给接收方）"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assigner_id != user.id:
        raise HTTPException(403, "只有发起方可以退回")
    if task.status != "completed_pending":
        raise HTTPException(400, f"当前状态({task.status})不能退回")

    task.status = "disputed"
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db), "message": "已退回，等待对方重新完成"}


@router.post("/{task_id}/forgive")
def forgive_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """接收方：原谅对方"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assignee_id != user.id:
        raise HTTPException(403, "只有接收方可以原谅")
    if task.card_item_id != "forgive_me":
        raise HTTPException(400, "该任务不是原谅卡任务")
    if task.status != "pending":
        raise HTTPException(400, f"当前状态({task.status})不能原谅")

    task.status = "completed"
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db), "message": "你原谅了对方 💕"}


@router.post("/{task_id}/reject")
def reject_forgive(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """接收方：不原谅"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assignee_id != user.id:
        raise HTTPException(403, "只有接收方可以决定是否原谅")
    if task.card_item_id != "forgive_me":
        raise HTTPException(400, "该任务不是原谅卡任务")
    if task.status != "pending":
        raise HTTPException(400, f"当前状态({task.status})不能操作")

    task.rejected = True
    task.rejected_at = datetime.now()
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db), "message": "已收到你的回应"}


@router.post("/{task_id}/retry")
def retry_forgive(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发起方：再次请求原谅"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assigner_id != user.id:
        raise HTTPException(403, "只有发起方可以再次请求")
    if task.card_item_id != "forgive_me":
        raise HTTPException(400, "该任务不是原谅卡任务")
    if task.status != "pending":
        raise HTTPException(400, f"当前状态({task.status})不能再次请求")
    if not task.rejected:
        raise HTTPException(400, "对方还没有拒绝，不需要再次请求")

    task.rejected = False
    task.rejected_at = None
    db.commit()
    return {"ok": True, "card_task": build_task_response(task, user, db), "message": "已再次请求原谅，等待对方的回应…"}


@router.post("/{task_id}/dismiss")
def dismiss_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发起方：确认原谅后立即收起"""
    task = db.query(CardTask).filter(CardTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assigner_id != user.id:
        raise HTTPException(403, "只有发起方可以确认")
    if task.card_item_id != "forgive_me":
        raise HTTPException(400, "仅支持原谅卡")
    # 直接删除任务，让列表立即清除
    db.delete(task)
    db.commit()
    return {"ok": True}
