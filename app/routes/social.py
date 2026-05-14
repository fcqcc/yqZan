import math
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.social import Level, LevelLog, Note
from app.models.user import User
from app.schemas.social import (
    AwardExpRequest,
    LevelLogResponse,
    LevelResponse,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["等级 & 便利贴"])


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


# ── 等级计算 ──

EXP_THRESHOLDS = [0]  # level 1
for n in range(2, 100):
    # 公式: 每级所需经验 ≈ 20 * n^1.8，累计形成总经验门槛
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
    cid = get_couple_id(user)
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
    cid = get_couple_id(user)
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
        notes.append(
            NoteResponse(
                id=n.id, content=n.content, image_url=n.image_url,
                likes=n.likes, liked=liked, user_id=n.user_id,
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
