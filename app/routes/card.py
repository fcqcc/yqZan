import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models.card import Card, CardTemplate
from app.models.couple import Couple
from app.models.extra import Anniversary, Gift, ToDo, ToDoCheckin
from app.models.plan import Delivery, Plan, Wish
from app.models.social import Level
from app.models.user import User
from app.schemas.card import (
    CardListResponse,
    CardResponse,
    GenerateCardRequest,
    TemplateResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["贺卡"])


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


# ── 预置模板 ──

PRESET_TEMPLATES = [
    {"name": "简约告白", "type": "template", "description": "简洁文字+背景，适合日常发送",
     "style_config": {"bg": "linear-gradient(135deg,#ffecd2,#fcb69f)", "font": "serif", "accent": "#d4380d"},
     "min_level": 1, "sort_order": 1},
    {"name": "浪漫之约", "type": "template", "description": "玫瑰金配色，适合纪念日",
     "style_config": {"bg": "linear-gradient(135deg,#fce4ec,#e8a0bf)", "font": "serif", "accent": "#ad1457"},
     "min_level": 1, "sort_order": 2},
    {"name": "星空物语", "type": "template", "description": "深蓝星空，适合跨年/生日",
     "style_config": {"bg": "linear-gradient(135deg,#0d1b2a,#1b3a5c)", "font": "sans", "accent": "#ffd54f"},
     "min_level": 3, "sort_order": 3},
    {"name": "年度总结", "type": "flip", "description": "翻页书效果，汇总全年数据",
     "style_config": {"bg": "linear-gradient(160deg,#221018,#9d2d5a)", "font": "serif", "accent": "#c9a227", "pages": True},
     "min_level": 1, "sort_order": 10},
    {"name": "纪念日快乐", "type": "auto", "description": "纪念日自动生成，含倒计时+祝福",
     "style_config": {"bg": "linear-gradient(135deg,#fce4ec,#f8bbd0)", "font": "serif", "accent": "#c62828"},
     "min_level": 1, "sort_order": 20},
    {"name": "目标达成", "type": "auto", "description": "存钱目标达成时自动生成",
     "style_config": {"bg": "linear-gradient(135deg,#e8f5e9,#a5d6a7)", "font": "sans", "accent": "#2e7d32"},
     "min_level": 1, "sort_order": 21},
]


def seed_templates(db: Session):
    """启动时自动插入预置模板（幂等）"""
    count = db.query(CardTemplate).count()
    if count > 0:
        return
    for t in PRESET_TEMPLATES:
        db.add(CardTemplate(**t))
    db.commit()


# 在导入时注册 seed（由 main.py 启动时调用）

# ── 数据快照生成 ──


def build_data_snapshot(couple_id: int, db: Session) -> dict:
    """收集情侣所有模块数据，用于生成贺卡"""
    now = datetime.now()
    today = now.date()

    # 存钱计划
    plans = db.query(Plan).filter(Plan.couple_id == couple_id).all()
    total_delivered = sum(p.current_amount or 0 for p in plans)
    total_target = sum(p.target_amount or 0 for p in plans)
    plan_count = len(plans)
    done_plans = sum(1 for p in plans if p.done)

    # 心愿
    wishes = db.query(Wish).filter(Wish.couple_id == couple_id).all()
    wish_count = len(wishes)
    fulfilled_wishes = sum(1 for w in wishes if w.status == "fulfilled")

    # 要做的事
    todos = db.query(ToDo).filter(ToDo.couple_id == couple_id).all()
    todo_count = len(todos)
    done_todos = sum(1 for t in todos if t.done)

    # 纪念日
    annis = db.query(Anniversary).filter(Anniversary.couple_id == couple_id).all()
    anni_count = len(annis)
    nearest_anni = None
    for a in annis:
        try:
            d = date.fromisoformat(a.date_val)
            # 计算下次
            ny = date(today.year, d.month, d.day)
            if ny < today:
                ny = date(today.year + 1, d.month, d.day)
            days_left = (ny - today).days
            if nearest_anni is None or days_left < nearest_anni["days_left"]:
                nearest_anni = {"title": a.title, "date": a.date_val, "days_left": days_left}
        except ValueError:
            pass

    # 礼物
    gifts = db.query(Gift).filter(Gift.couple_id == couple_id).all()
    gift_count = len(gifts)
    total_gift_amount = sum(g.price or 0 for g in gifts)

    # 等级
    level = db.query(Level).filter(Level.couple_id == couple_id).first()
    lvl = level.level if level else 1
    exp = level.total_exp_earned if level else 0

    # 注册天数
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    reg_days = (now - couple.created_at).days if couple and couple.created_at else 0

    # 便利贴
    note_count = db.query(Note).filter(Note.couple_id == couple_id).count() if 'Note' in dir() else 0

    return {
        "generated_at": now.isoformat(),
        "total_delivered": total_delivered,
        "total_target": total_target,
        "plan_count": plan_count,
        "done_plans": done_plans,
        "plan_progress": round(total_delivered / max(total_target, 1) * 100, 1),
        "wish_count": wish_count,
        "fulfilled_wishes": fulfilled_wishes,
        "wish_rate": round(fulfilled_wishes / max(wish_count, 1) * 100, 1),
        "todo_count": todo_count,
        "done_todos": done_todos,
        "todo_rate": round(done_todos / max(todo_count, 1) * 100, 1),
        "anni_count": anni_count,
        "nearest_anni": nearest_anni,
        "gift_count": gift_count,
        "total_gift_amount": total_gift_amount,
        "level": lvl,
        "total_exp": exp,
        "together_days": reg_days,
        "note_count": note_count,
        "last_updated": now.strftime("%Y年%m月%d日"),
    }


# ── API ──


@router.get("/card/templates", response_model=list[TemplateResponse])
def list_templates(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # seed handled by startup event
    cid = get_couple_id(user)
    level = db.query(Level).filter(Level.couple_id == cid).first()
    user_level = level.level if level else 1

    templates = (
        db.query(CardTemplate)
        .filter(CardTemplate.min_level <= user_level)
        .order_by(CardTemplate.sort_order, CardTemplate.id)
        .all()
    )

    result = []
    for t in templates:
        result.append(TemplateResponse.model_validate(t))
    return result


@router.get("/card/snapshot")
def get_snapshot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    return build_data_snapshot(cid, db)


@router.post("/card/generate")
def generate_card(
    req: GenerateCardRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)

    template = db.query(CardTemplate).filter(CardTemplate.id == req.template_id).first()
    if not template:
        raise HTTPException(404, "模板不存在")

    # 检查等级
    level = db.query(Level).filter(Level.couple_id == cid).first()
    user_level = level.level if level else 1
    if template.min_level > user_level:
        raise HTTPException(403, f"需要Lv{template.min_level}才能使用此模板")

    snapshot = build_data_snapshot(cid, db)

    card = Card(
        couple_id=cid,
        template_id=template.id,
        type=template.type,
        title=req.title or template.name,
        message=req.message,
        data_snapshot=json.dumps(snapshot, ensure_ascii=False),
        trigger_event=req.trigger_event,
        event_ref_id=req.event_ref_id,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    return {
        "ok": True,
        "card_id": card.id,
        "type": card.type,
        "title": card.title,
        "data_snapshot": snapshot,
    }


@router.get("/cards", response_model=CardListResponse)
def list_cards(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    rows = db.query(Card).filter(Card.couple_id == cid).order_by(Card.created_at.desc()).all()
    cards = []
    for c in rows:
        snap = json.loads(c.data_snapshot) if isinstance(c.data_snapshot, str) else c.data_snapshot
        cards.append(CardResponse(
            id=c.id, template_id=c.template_id, type=c.type,
            title=c.title, message=c.message,
            data_snapshot=snap, image_url=c.image_url,
            trigger_event=c.trigger_event, read=c.read,
            created_at=c.created_at,
        ))
    return CardListResponse(cards=cards)


@router.get("/cards/{card_id}", response_model=CardResponse)
def get_card(
    card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    c = db.query(Card).filter(Card.id == card_id, Card.couple_id == cid).first()
    if not c:
        raise HTTPException(404, "贺卡不存在")
    snap = json.loads(c.data_snapshot) if isinstance(c.data_snapshot, str) else c.data_snapshot
    return CardResponse(
        id=c.id, template_id=c.template_id, type=c.type,
        title=c.title, message=c.message,
        data_snapshot=snap, image_url=c.image_url,
        trigger_event=c.trigger_event, read=c.read,
        created_at=c.created_at,
    )


@router.post("/cards/{card_id}/read")
def mark_read(
    card_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    c = db.query(Card).filter(Card.id == card_id, Card.couple_id == cid).first()
    if not c:
        raise HTTPException(404, "贺卡不存在")
    if c.read == 0:
        c.read = 1
        db.commit()
    return {"ok": True}
