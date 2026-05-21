import math
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.social import Level, LevelLog, Note, Task, TaskEvent
from app.models.user import User
from app.schemas.social import (
    AwardExpRequest,
    LevelLogResponse,
    LevelResponse,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    TaskCreate,
    TaskEventAccept,
    TaskEventResponse,
    TaskResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["等级 & 便利贴"])


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


# ── 等级计算 ──

# 手动设定前15级的累计经验门槛（让前期升级飞快）
EARLY_THRESHOLDS = [0, 10, 25, 45, 70, 100, 140, 190, 250, 320, 400, 490, 590, 700, 820]

EXP_THRESHOLDS = list(EARLY_THRESHOLDS)  # level 1-15
for n in range(len(EARLY_THRESHOLDS) + 1, 100):
    # 从第16级起用原公式 20 * n^1.8
    EXP_THRESHOLDS.append(int(20 * (n**1.8)))


def calc_level(total_exp: int) -> tuple[int, int, int, float]:
    """return (current_level, current_exp_in_level, exp_for_next_level, progress_pct)"""
    if total_exp <= 0:
        return (1, 0, EXP_THRESHOLDS[1], 0.0)

    for lvl in range(1, 99):
        threshold = EXP_THRESHOLDS[lvl - 1]
        next_th = EXP_THRESHOLDS[lvl] if lvl < 98 else 999999
        if total_exp < next_th:
            in_level = total_exp - threshold
            needed = next_th - threshold
            pct = round(in_level / max(needed, 1) * 100, 1)
            return (lvl, in_level, needed, pct)

    return (99, 0, 0, 100.0)


def get_or_create_level(couple_id: int, db: Session) -> Level:
    level = db.query(Level).filter(Level.couple_id == couple_id).first()
    if not level:
        level = Level(couple_id=couple_id, level=1, current_exp=0, total_exp_earned=0)
        db.add(level)
        db.flush()
    return level


def add_exp(couple_id: int, amount: int, reason: str, db: Session) -> Level:
    level = get_or_create_level(couple_id, db)
    old_level = level.level

    level.current_exp += amount
    level.total_exp_earned += amount

    # Recalculate level
    new_lvl, _, _, _ = calc_level(level.total_exp_earned)
    if new_lvl > old_level:
        level.pending_levelups += new_lvl - old_level
    level.level = new_lvl
    level.updated_at = datetime.now()

    db.add(LevelLog(couple_id=couple_id, amount=amount, reason=reason))
    db.commit()
    db.refresh(level)
    return level


# ===================== 等级 API =====================


@router.get("/level", response_model=LevelResponse)
def get_level(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return LevelResponse(level=1, current_exp=0, total_exp_earned=0, next_level_exp=20, progress_pct=0.0, pending_levelups=0)
    level = get_or_create_level(cid, db)
    lvl, in_level, needed, pct = calc_level(level.total_exp_earned)
    return LevelResponse(
        level=lvl,
        current_exp=in_level,
        total_exp_earned=level.total_exp_earned,
        next_level_exp=needed,
        progress_pct=pct,
        pending_levelups=level.pending_levelups,
    )


@router.get("/level/logs", response_model=list[LevelLogResponse])
def get_level_logs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    return (
        db.query(LevelLog)
        .filter(LevelLog.couple_id == cid)
        .order_by(LevelLog.created_at.desc())
        .limit(50)
        .all()
    )


@router.post("/level/award")
def award_exp(
    req: AwardExpRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """其他模块调用此接口给用户加经验"""
    cid = get_couple_id(user)
    level = add_exp(cid, req.amount, req.reason, db)
    lvl, in_level, needed, pct = calc_level(level.total_exp_earned)
    return {
        "ok": True,
        "level": lvl,
        "current_exp": in_level,
        "next_level_exp": needed,
        "progress_pct": pct,
        "pending_levelups": level.pending_levelups,
    }


@router.post("/level/consume-pending")
def consume_pending(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """小程序展示完升级动画后调用，清除pending_levelups"""
    cid = get_couple_id(user)
    level = get_or_create_level(cid, db)
    level.pending_levelups = 0
    db.commit()
    return {"ok": True}


# ── 等级解锁系统 ──

LEVEL_UNLOCKS = [
    {"level": 1,  "feature": "basic",          "name": "基础功能",               "desc": "1个存钱计划、3个宠物位"},
    {"level": 3,  "feature": "plan_slot_2",    "name": "存钱计划+1",            "desc": "可同时进行2个存钱计划"},
    {"level": 5,  "feature": "pet_slot_4",     "name": "宠物位+1",              "desc": "可拥有4只宠物"},
    {"level": 8,  "feature": "note_color",     "name": "留言字体颜色",          "desc": "留言可更换字体颜色"},
    {"level": 10, "feature": "plan_slot_3",    "name": "存钱计划+1",            "desc": "可同时进行3个存钱计划"},
    {"level": 12, "feature": "shop_limited",   "name": "限量外观商城",          "desc": "积分商城解锁限量头像框和背景"},
    {"level": 15, "feature": "pet_slot_5",     "name": "宠物位+1",              "desc": "可拥有全部5只宠物"},
    {"level": 18, "feature": "boost_upgrade",  "name": "强化积分加注",          "desc": "抽卡积分加注上限提升至100💎"},
    {"level": 20, "feature": "spark_custom",   "name": "火花自定义图标",        "desc": "可自定义火花显示图标"},
    {"level": 25, "feature": "plan_slot_4",    "name": "存钱计划+1",            "desc": "可同时进行最多4个存钱计划"},
    {"level": 30, "feature": "pk_arena",       "name": "情侣PK周榜",            "desc": "解锁情侣存钱PK排行榜"},
    {"level": 40, "feature": "note_sticker",   "name": "留言贴图",              "desc": "留言可插入自定义表情/贴图"},
    {"level": 50, "feature": "pet_frame",      "name": "宠物展示框",            "desc": "宠物页面获得特殊金色展示框"},
]


@router.get("/level/unlocks")
def get_level_unlocks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前等级已解锁/即将解锁的功能"""
    cid = user.couple_id
    if not cid:
        return {"current_level": 1, "unlocked": [], "next_unlock": None, "all": LEVEL_UNLOCKS}

    from app.models.social import Level as Lvl
    level = db.query(Lvl).filter(Lvl.couple_id == cid).first()
    current_level = level.level if level else 1

    unlocked = [u for u in LEVEL_UNLOCKS if u["level"] <= current_level]
    next_unlock = next((u for u in LEVEL_UNLOCKS if u["level"] > current_level), None)

    return {
        "current_level": current_level,
        "unlocked": unlocked,
        "next_unlock": next_unlock,
        "all": LEVEL_UNLOCKS,
    }


# ===================== 便利贴墙 =====================


@router.get("/notes", response_model=NoteListResponse)
def list_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    rows = (
        db.query(Note)
        .filter(Note.couple_id == cid)
        .order_by(Note.created_at.desc())
        .all()
    )
    notes = []
    for n in rows:
        liked = str(user.id) in (n.liked_by or "").split(",")
        stamped = str(user.id) in (n.stamped_by or "").split(",")
        notes.append(
            NoteResponse(
                id=n.id, content=n.content, image_url=n.image_url,
                likes=n.likes, liked=liked, stamped=stamped, user_id=n.user_id,
                created_at=n.created_at,
            )
        )
    return NoteListResponse(notes=notes)


@router.post("/notes")
def create_note(
    req: NoteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    note = Note(couple_id=cid, user_id=user.id, content=req.content, image_url=req.image_url)
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"ok": True, "note_id": note.id}


@router.post("/notes/{note_id}/like")
def toggle_like(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    note = db.query(Note).filter(Note.id == note_id, Note.couple_id == cid).first()
    if not note:
        raise HTTPException(404, "便利贴不存在")

    user_ids = set(note.liked_by.split(",")) if note.liked_by else set()
    uid_str = str(user.id)

    if uid_str in user_ids:
        user_ids.discard(uid_str)
        note.likes = max(0, note.likes - 1)
    else:
        user_ids.add(uid_str)
        note.likes += 1

    note.liked_by = ",".join(sorted(user_ids, key=int))
    db.commit()
    return {"ok": True, "likes": note.likes, "liked": uid_str in user_ids}


@router.post("/notes/{note_id}/stamp")
def toggle_stamp(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    note = db.query(Note).filter(Note.id == note_id, Note.couple_id == cid).first()
    if not note:
        raise HTTPException(404, "留言不存在")
    if note.user_id == user.id:
        raise HTTPException(400, "不能给自己的留言盖章")

    user_ids = set(note.stamped_by.split(",")) if note.stamped_by else set()
    uid_str = str(user.id)
    if uid_str in user_ids:
        user_ids.discard(uid_str)
        stamped = False
    else:
        user_ids.add(uid_str)
        stamped = True

    note.stamped_by = ",".join(sorted(user_ids, key=int))
    db.commit()
    return {"ok": True, "stamped": stamped}


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    note = db.query(Note).filter(Note.id == note_id, Note.couple_id == cid).first()
    if not note:
        raise HTTPException(404, "便利贴不存在")
    if note.user_id != user.id:
        raise HTTPException(403, "只能删除自己的留言")
    db.delete(note)
    db.commit()
    return {"ok": True}


# ===================== 情侣任务 =====================

def _get_couple_id(user):
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def _add_exp(couple_id, amount, reason, db):
    """添加经验并检查升级"""
    from app.models.social import Level as Lvl, LevelLog as LvlLog
    level = db.query(Lvl).filter(Lvl.couple_id == couple_id).first()
    if not level:
        level = Lvl(couple_id=couple_id)
        db.add(level)
        db.flush()
    
    old_lvl = level.level
    level.current_exp += amount
    level.total_exp_earned += amount
    
    # 重新计算等级
    new_lvl = 1
    for i, t in enumerate(EXP_THRESHOLDS, 1):
        if level.total_exp_earned >= t:
            new_lvl = i
    
    if new_lvl > old_lvl:
        level.pending_levelups += new_lvl - old_lvl
    level.level = new_lvl
    level.updated_at = datetime.now()
    
    db.add(LvlLog(couple_id=couple_id, amount=amount, reason=reason))
    db.commit()
    return level


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_couple_id(user)
    tasks = (
        db.query(Task)
        .filter(Task.couple_id == cid)
        .order_by(Task.created_at.desc())
        .all()
    )
    return tasks


@router.get("/tasks/events", response_model=list[TaskEventResponse])
def list_task_events(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出可接取的官方事件任务"""
    cid = _get_couple_id(user)
    events = db.query(TaskEvent).filter(TaskEvent.active == True).all()
    
    # 过滤已接取的
    accepted = db.query(Task.event_code).filter(
        Task.couple_id == cid,
        Task.type == "event",
        Task.event_code.isnot(None),
    ).all()
    accepted_codes = {a[0] for a in accepted if a[0]}
    
    result = []
    for e in events:
        if e.event_code not in accepted_codes:
            result.append(e)
    return result


@router.post("/tasks")
def create_task(
    req: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """给伴侣指派任务"""
    cid = _get_couple_id(user)
    
    # 验证被指派者是伴侣
    assignee = db.query(User).filter(
        User.id == req.assignee_id,
        User.couple_id == cid,
        User.id != user.id,
    ).first()
    if not assignee:
        raise HTTPException(400, "只能给伴侣指派任务")
    
    task = Task(
        couple_id=cid,
        assigner_id=user.id,
        assignee_id=req.assignee_id,
        type="personal",
        category=req.category,
        title=req.title,
        note=req.note,
        deadline=req.deadline,
        exp_reward=5,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"ok": True, "task_id": task.id}


@router.post("/tasks/accept")
def accept_task_event(
    req: TaskEventAccept,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """接取官方事件任务"""
    cid = _get_couple_id(user)
    
    event = db.query(TaskEvent).filter(
        TaskEvent.event_code == req.event_code,
        TaskEvent.active == True,
    ).first()
    if not event:
        raise HTTPException(404, "事件任务不存在")
    
    # 检查是否已接取
    existing = db.query(Task).filter(
        Task.couple_id == cid,
        Task.type == "event",
        Task.event_code == req.event_code,
    ).first()
    if existing:
        raise HTTPException(400, "已接取此事件任务")
    
    # 找伴侣
    partner = db.query(User).filter(
        User.couple_id == cid,
        User.id != user.id,
    ).first()
    partner_id = partner.id if partner else user.id
    
    task = Task(
        couple_id=cid,
        assigner_id=user.id,
        assignee_id=partner_id,
        type="event",
        event_code=event.event_code,
        category=event.category,
        title=event.title,
        note=event.description,
        exp_reward=event.exp_reward,
        status="accepted",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"ok": True, "task_id": task.id}


@router.post("/tasks/{task_id}/verify")
def verify_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """完成验收任务（发布者验收）"""
    cid = _get_couple_id(user)
    task = db.query(Task).filter(Task.id == task_id, Task.couple_id == cid).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.assigner_id != user.id:
        raise HTTPException(403, "只有发布者可以验收")
    if task.status == "verified":
        raise HTTPException(400, "任务已验收")
    
    task.status = "verified"
    
    # 加经验
    _add_exp(cid, task.exp_reward, f"完成任务：{task.title}", db)
    
    db.commit()
    return {"ok": True, "exp_reward": task.exp_reward}


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = _get_couple_id(user)
    task = db.query(Task).filter(Task.id == task_id, Task.couple_id == cid).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    db.delete(task)
    db.commit()
    return {"ok": True}
