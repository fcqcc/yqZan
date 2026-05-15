import json
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.card import Card
from app.models.couple import Couple
from app.models.extra import Anniversary, Gift, ToDo
from app.models.plan import Delivery, Plan, Wish
from app.models.social import Level, LevelLog, Note
from app.models.user import User

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ── Admin auth helpers ──

def verify_admin(request: Request) -> None:
    """Check if admin is logged in via cookie"""
    token = request.cookies.get("admin_token")
    if token != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=303, detail="需要登录")


# ── Login ──

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": ""})


@router.post("/login", response_class=HTMLResponse, include_in_schema=False)
def login_action(
    request: Request,
    password: str = Form(...),
):
    if password != settings.ADMIN_PASSWORD:
        return templates.TemplateResponse(request, "admin/login.html", {"error": "密码错误"})
    resp = RedirectResponse(url="/admin", status_code=303)
    resp.set_cookie(key="admin_token", value=password, httponly=True, max_age=86400)
    return resp


@router.get("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("admin_token")
    return resp


# ── Dashboard ──

@router.get("", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    total_users = db.query(func.count(User.id)).scalar()
    total_couples = db.query(func.count(Couple.id)).filter(Couple.status == "active").scalar()
    archived_couples = db.query(func.count(Couple.id)).filter(Couple.status == "archived").scalar()
    unbound_users = db.query(func.count(User.id)).filter(User.couple_id.is_(None)).scalar()
    total_plans = db.query(func.count(Plan.id)).scalar()
    total_wishes = db.query(func.count(Wish.id)).scalar()

    # 今日新增
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar()

    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {
            "total_users": total_users,
            "total_couples": total_couples,
            "archived_couples": archived_couples,
            "unbound_users": unbound_users,
            "total_plans": total_plans,
            "total_wishes": total_wishes,
            "new_users_today": new_users_today,
            "active_page": "dashboard",
        },
    )


# ── Users ──

@router.get("/users", response_class=HTMLResponse, include_in_schema=False)
def admin_users(
    request: Request,
    page: int = 1,
    q: str = "",
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    per_page = 30
    query = db.query(User).order_by(User.created_at.desc())

    if q:
        query = query.filter(User.nickname.contains(q))

    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()

    # 补充伴侣信息
    user_list = []
    for u in users:
        partner_name = ""
        if u.couple_id:
            partner = (
                db.query(User)
                .filter(User.couple_id == u.couple_id, User.id != u.id)
                .first()
            )
            partner_name = partner.nickname if partner else "(已解绑)"

        couple = db.query(Couple).filter(Couple.id == u.couple_id).first() if u.couple_id else None
        couple_status = couple.status if couple else ""

        user_list.append({
            "id": u.id,
            "nickname": u.nickname,
            "birthday": u.birthday,
            "gender": u.gender,
            "invite_code": u.invite_code,
            "couple_id": u.couple_id,
            "partner_name": partner_name,
            "couple_status": couple_status,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return templates.TemplateResponse(
        request, "admin/users.html",
        {
            "users": user_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "q": q,
            "active_page": "users",
        },
    )


# ── Couples ──

@router.get("/couples", response_class=HTMLResponse, include_in_schema=False)
def admin_couples(
    request: Request,
    page: int = 1,
    status_filter: str = "active",
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    per_page = 20
    query = db.query(Couple).order_by(Couple.created_at.desc())
    if status_filter in ("active", "archived"):
        query = query.filter(Couple.status == status_filter)

    total = query.count()
    active_count = db.query(func.count(Couple.id)).filter(Couple.status == "active").scalar()
    couples = query.offset((page - 1) * per_page).limit(per_page).all()

    couple_list = []
    for c in couples:
        members = db.query(User).filter(User.couple_id == c.id).all()
        member_names = [m.nickname for m in members]
        member_str = " & ".join(member_names) if member_names else "(无成员)"

        # 统计数据
        plan_count = db.query(func.count(Plan.id)).filter(Plan.couple_id == c.id).scalar()
        wish_count = db.query(func.count(Wish.id)).filter(Wish.couple_id == c.id).scalar()
        gift_count = db.query(func.count(Gift.id)).filter(Gift.couple_id == c.id).scalar()

        couple_list.append({
            "id": c.id,
            "members": member_str,
            "status": c.status,
            "plan_count": plan_count,
            "wish_count": wish_count,
            "gift_count": gift_count,
            "created_at": c.created_at.strftime("%Y-%m-%d"),
            "archived_at": c.archived_at.strftime("%Y-%m-%d") if c.archived_at else "",
        })

    return templates.TemplateResponse(
        request, "admin/couples.html",
        {
            "couples": couple_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "status_filter": status_filter,
            "active_count": active_count,
            "active_page": "couples",
        },
    )


# ── Health ──

@router.get("/health", response_class=HTMLResponse, include_in_schema=False)
def admin_health(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    checks = []

    # 数据库
    try:
        db.execute(func.count(User.id))
        db_status = "✅ 正常"
    except Exception:
        db_status = "❌ 异常"
    checks.append(("数据库", db_status))

    # API 自检
    try:
        user_count = db.query(func.count(User.id)).scalar()
        api_status = f"✅ {user_count} 用户"
    except Exception:
        api_status = "❌ 异常"
    checks.append(("API", api_status))

    # 磁盘（简单检查）
    import os
    try:
        stat = os.statvfs("/")
        free_gb = stat.f_bavail * stat.f_frsize / 1024 / 1024 / 1024
        disk_status = f"✅ 剩余 {free_gb:.1f}GB"
    except Exception:
        disk_status = "❌ 无法读取"
    checks.append(("磁盘", disk_status))

    # 运行时间
    uptime_seconds = time.time() - __import__("os").popen("date +%s").read().strip().__int__()
    uptime_hours = int(uptime_seconds) // 3600
    uptime_status = f"✅ {uptime_hours}h"

    return templates.TemplateResponse(
        request, "admin/health.html",
        {
            "checks": checks,
            "uptime": uptime_status,
            "active_page": "health",
        },
    )
