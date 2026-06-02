import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.draw import DrawCategory, DrawItem
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["今日签"])

# ===== 预置数据（情侣向） =====
PRESET_CATEGORIES = [
    {"name": "吃什么", "icon": "🍜", "items": [
        "火锅", "烧烤", "日料", "川菜", "粤菜", "西餐", "东南亚菜",
        "酸菜鱼", "小龙虾", "螺蛳粉", "自己做顿好的", "外卖随便点",
        "韩式烤肉", "麻辣烫", "饺子", "寿司"
    ]},
    {"name": "玩什么", "icon": "🎮", "items": [
        "看电影", "逛街逛商场", "打游戏", "剧本杀", "密室逃脱",
        "KTV唱歌", "玩桌游", "散步压马路", "去露营", "看展览",
        "做手工", "一起烘焙", "逛宜家", "泡图书馆", "骑车兜风"
    ]},
    {"name": "去哪里", "icon": "📍", "items": [
        "去商场", "去公园", "去海边", "去图书馆", "去咖啡厅",
        "去游乐园", "去博物馆", "去健身房", "去夜市", "去爬山",
        "去江边散步", "去动物园", "去电影院"
    ]},
    {"name": "先干啥", "icon": "🎯", "items": [
        "先学习/工作2小时", "先做完家务", "先运动半小时",
        "先玩再学", "先睡一觉再说", "先出门再说",
        "先收拾房间", "先洗澡放松", "先一起吃个饭"
    ]},
    {"name": "情侣任务", "icon": "💝", "items": [
        "给对方写一封信", "一起做一顿饭", "拍一组合照",
        "互相按摩10分钟", "一起看日落", "一起逛超市",
        "给对方一个惊喜", "一起敷面膜", "一起听一张专辑",
        "一起看老照片", "互相夸对方3个优点"
    ]},
]


def get_couple_id(user: User) -> int:
    if not user.couple_id:
        raise HTTPException(400, "未绑定伴侣")
    return user.couple_id


def seed_presets(couple_id: int, db: Session):
    """首次使用：写入预置分类和条目"""
    existing = db.query(DrawCategory).filter(
        DrawCategory.couple_id == couple_id,
        DrawCategory.is_default == True
    ).first()
    if existing:
        return
    for i, cat in enumerate(PRESET_CATEGORIES):
        c = DrawCategory(
            couple_id=couple_id,
            name=cat["name"],
            icon=cat["icon"],
            sort_order=i,
            is_default=True,
        )
        db.add(c)
        db.flush()
        for content in cat["items"]:
            db.add(DrawItem(
                category_id=c.id,
                couple_id=couple_id,
                content=content,
                is_custom=False,
            ))
    db.commit()


# ===================== API =====================


@router.get("/draw/categories")
def list_categories(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    seed_presets(cid, db)
    cats = (
        db.query(DrawCategory)
        .filter(DrawCategory.couple_id == cid)
        .order_by(DrawCategory.sort_order)
        .all()
    )
    result = []
    for c in cats:
        count = db.query(DrawItem).filter(DrawItem.category_id == c.id).count()
        result.append({
            "id": c.id,
            "name": c.name,
            "icon": c.icon or "🎯",
            "sort_order": c.sort_order,
            "is_default": c.is_default,
            "item_count": count,
        })
    return result


@router.post("/draw/categories")
def create_category(
    req: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    name = (req.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "请填写分类名称")
    icon = (req.get("icon") or "🎯").strip()
    max_order = db.query(DrawCategory.sort_order).filter(
        DrawCategory.couple_id == cid
    ).order_by(DrawCategory.sort_order.desc()).first()
    next_order = (max_order[0] + 1) if max_order else 0
    cat = DrawCategory(couple_id=cid, name=name, icon=icon, sort_order=next_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"ok": True, "id": cat.id}


@router.delete("/draw/categories/{cat_id}")
def delete_category(
    cat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    cat = db.query(DrawCategory).filter(
        DrawCategory.id == cat_id, DrawCategory.couple_id == cid
    ).first()
    if not cat:
        raise HTTPException(404, "分类不存在")
    if cat.is_default:
        raise HTTPException(400, "预置分类不能删除")
    db.query(DrawItem).filter(DrawItem.category_id == cat_id).delete()
    db.delete(cat)
    db.commit()
    return {"ok": True}


@router.get("/draw/items")
def list_items(
    category_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = user.couple_id
    if not cid:
        return []
    items = (
        db.query(DrawItem)
        .filter(DrawItem.category_id == category_id, DrawItem.couple_id == cid)
        .order_by(DrawItem.is_custom, DrawItem.id)
        .all()
    )
    return [{
        "id": i.id,
        "content": i.content,
        "is_custom": i.is_custom,
        "used_count": i.used_count,
    } for i in items]


@router.post("/draw/items")
def create_item(
    req: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    content = (req.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "请填写内容")
    category_id = req.get("category_id")
    if not category_id:
        raise HTTPException(400, "请指定分类")
    cat = db.query(DrawCategory).filter(
        DrawCategory.id == category_id, DrawCategory.couple_id == cid
    ).first()
    if not cat:
        raise HTTPException(404, "分类不存在")
    item = DrawItem(
        category_id=category_id,
        couple_id=cid,
        content=content,
        is_custom=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}


@router.delete("/draw/items/{item_id}")
def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = get_couple_id(user)
    item = db.query(DrawItem).filter(
        DrawItem.id == item_id, DrawItem.couple_id == cid
    ).first()
    if not item:
        raise HTTPException(404, "条目不存在")
    if not item.is_custom:
        raise HTTPException(400, "预置条目不能删除")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/draw")
def do_draw(
    req: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从指定分类随机抽取一个条目"""
    cid = get_couple_id(user)
    category_id = req.get("category_id")
    if not category_id:
        raise HTTPException(400, "请指定分类")
    items = (
        db.query(DrawItem)
        .filter(DrawItem.category_id == category_id, DrawItem.couple_id == cid)
        .all()
    )
    if not items:
        raise HTTPException(404, "该分类还没有选项，先添加一些吧")
    picked = random.choice(items)
    picked.used_count = (picked.used_count or 0) + 1
    db.commit()
    cat = db.query(DrawCategory).filter(DrawCategory.id == category_id).first()
    return {
        "ok": True,
        "item": {
            "id": picked.id,
            "content": picked.content,
            "category_name": cat.name if cat else "",
            "category_icon": cat.icon if cat else "🎯",
        }
    }
