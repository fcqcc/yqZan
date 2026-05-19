from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.extra import Anniversary, Gift, ToDo, ToDoCheckin
from app.models.user import User
from app.schemas.extra import (
    AnniversaryCreate,
    AnniversaryResponse,
    AnniversaryUpdate,
    GiftCreate,
    GiftResponse,
    ToDoCheckinResponse,
    ToDoCreate,
    ToDoResponse,
    ToDoUpdate,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["要做 & 纪念日 & 礼物"])


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


# ===================== 要做的事 =====================


@router.get("/todos", response_model=list[ToDoResponse])
def list_todos(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    todos = db.query(ToDo).filter(ToDo.couple_id == cid).order_by(ToDo.created_at.desc()).all()
    result = []
    for t in todos:
        checkins = (
            db.query(ToDoCheckin)
            .filter(ToDoCheckin.todo_id == t.id)
            .order_by(ToDoCheckin.created_at.desc())
            .all()
        )
        result.append(
            ToDoResponse(
                id=t.id, scope=t.scope, type=t.type, title=t.title,
                note=t.note, deadline=t.deadline,
                cycle_total=t.cycle_total, cycle_current=t.cycle_current,
                done=t.done, creator_id=t.creator_id,
                checkins=[ToDoCheckinResponse.model_validate(c) for c in checkins],
                created_at=t.created_at,
            )
        )
    return result


@router.post("/todos")
def create_todo(
    req: ToDoCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    todo = ToDo(
        couple_id=cid, creator_id=user.id,
        scope=req.scope, type=req.type, title=req.title,
        note=req.note, deadline=req.deadline,
        cycle_total=req.cycle_total,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return {"ok": True, "todo_id": todo.id}


@router.put("/todos/{todo_id}")
def update_todo(
    todo_id: int,
    req: ToDoUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    todo = db.query(ToDo).filter(ToDo.id == todo_id, ToDo.couple_id == cid).first()
    if not todo:
        raise HTTPException(404, "事项不存在")
    if req.title is not None:
        todo.title = req.title
    if req.note is not None:
        todo.note = req.note
    if req.deadline is not None:
        todo.deadline = req.deadline
    if req.cycle_total is not None:
        todo.cycle_total = req.cycle_total
    if req.done is not None:
        todo.done = req.done
    todo.created_at = datetime.now()  # bump for reorder
    db.commit()
    return {"ok": True}


@router.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    todo = db.query(ToDo).filter(ToDo.id == todo_id, ToDo.couple_id == cid).first()
    if not todo:
        raise HTTPException(404, "事项不存在")
    db.query(ToDoCheckin).filter(ToDoCheckin.todo_id == todo_id).delete()
    db.delete(todo)
    db.commit()
    return {"ok": True}


@router.post("/todos/{todo_id}/checkin")
def checkin_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    todo = db.query(ToDo).filter(ToDo.id == todo_id, ToDo.couple_id == cid).first()
    if not todo:
        raise HTTPException(404, "事项不存在")

    if todo.scope == "alone" and todo.creator_id != user.id:
        raise HTTPException(403, "这是对方的个人事项，你不能打卡")

    if todo.type == "short_term":
        todo.done = True
    else:
        todo.cycle_current = (todo.cycle_current or 0) + 1
        if todo.cycle_total > 0 and todo.cycle_current >= todo.cycle_total:
            todo.done = True

    checkin = ToDoCheckin(todo_id=todo_id, user_id=user.id)
    db.add(checkin)
    db.commit()
    return {"ok": True, "done": todo.done, "cycle_current": todo.cycle_current}


# ===================== 纪念日 =====================


@router.get("/anniversaries", response_model=list[AnniversaryResponse])
def list_anniversaries(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    return (
        db.query(Anniversary)
        .filter(Anniversary.couple_id == cid)
        .order_by(Anniversary.date_val)
        .all()
    )


@router.post("/anniversaries")
def create_anniversary(
    req: AnniversaryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    existing = (
        db.query(Anniversary)
        .filter(
            Anniversary.couple_id == cid,
            Anniversary.title == req.title,
            Anniversary.date_val == req.date_val,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "这个纪念日已存在")

    anni = Anniversary(couple_id=cid, title=req.title, date_val=req.date_val)
    db.add(anni)
    db.commit()
    db.refresh(anni)
    return {"ok": True, "anniversary_id": anni.id}


@router.put("/anniversaries/{anni_id}")
def update_anniversary(
    anni_id: int,
    req: AnniversaryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    anni = db.query(Anniversary).filter(Anniversary.id == anni_id, Anniversary.couple_id == cid).first()
    if not anni:
        raise HTTPException(404, "纪念日不存在")
    if req.title is not None:
        anni.title = req.title
    if req.date_val is not None:
        anni.date_val = req.date_val
    if req.remind is not None:
        anni.remind = req.remind
    db.commit()
    return {"ok": True}


@router.delete("/anniversaries/{anni_id}")
def delete_anniversary(
    anni_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    anni = db.query(Anniversary).filter(Anniversary.id == anni_id, Anniversary.couple_id == cid).first()
    if not anni:
        raise HTTPException(404, "纪念日不存在")
    db.delete(anni)
    db.commit()
    return {"ok": True}


# ── 一键导入节日 ──

COUPLE_HOLIDAYS_2026 = [
    {"title": "元旦", "date": "2026-01-01", "emoji": "🎊"},
    {"title": "情人节", "date": "2026-02-14", "emoji": "💕"},
    {"title": "白色情人节", "date": "2026-03-14", "emoji": "🤍"},
    {"title": "520网络情人节", "date": "2026-05-20", "emoji": "💖"},
    {"title": "521网络情人节", "date": "2026-05-21", "emoji": "💖"},
    {"title": "七夕节", "date": "2026-08-19", "emoji": "💑"},
    {"title": "平安夜", "date": "2026-12-24", "emoji": "🎄"},
    {"title": "圣诞节", "date": "2026-12-25", "emoji": "🎅"},
    {"title": "跨年夜", "date": "2026-12-31", "emoji": "🎆"},
]


@router.get("/anniversaries/holiday-list")
def get_holiday_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取可导入的节日列表（标记已存在）"""
    cid = get_couple_id(user)
    existing = {
        a.title for a in db.query(Anniversary).filter(Anniversary.couple_id == cid).all()
    }
    return [
        {**h, "existing": h["title"] in existing}
        for h in COUPLE_HOLIDAYS_2026
    ]


@router.post("/anniversaries/import-holidays")
def import_holidays(
    req: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导入勾选的节日"""
    cid = get_couple_id(user)
    titles = req.get("titles", [])
    if not titles:
        raise HTTPException(400, "请选择至少一个节日")
    existing = {
        a.title for a in db.query(Anniversary).filter(Anniversary.couple_id == cid).all()
    }
    holiday_map = {h["title"]: h for h in COUPLE_HOLIDAYS_2026}
    imported = 0
    for title in titles:
        if title in existing:
            continue
        h = holiday_map.get(title)
        if not h:
            continue
        db.add(Anniversary(couple_id=cid, title=title, date_val=h["date"]))
        imported += 1
    db.commit()
    return {"ok": True, "imported": imported}


# ===================== 礼物记录 =====================


@router.get("/gifts", response_model=list[GiftResponse])
def list_gifts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    return (
        db.query(Gift)
        .filter(Gift.couple_id == cid)
        .order_by(Gift.created_at.desc())
        .all()
    )


@router.post("/gifts")
def create_gift(
    req: GiftCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    gift = Gift(
        couple_id=cid, user_id=user.id,
        name=req.name, date_val=req.date_val,
        note=req.note, price=req.price,
    )
    db.add(gift)
    db.commit()
    db.refresh(gift)
    return {"ok": True, "gift_id": gift.id}


@router.delete("/gifts/{gift_id}")
def delete_gift(
    gift_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    gift = db.query(Gift).filter(Gift.id == gift_id, Gift.couple_id == cid).first()
    if not gift:
        raise HTTPException(404, "礼物记录不存在")
    db.delete(gift)
    db.commit()
    return {"ok": True}
