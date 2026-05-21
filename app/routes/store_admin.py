import random
import string
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.store import CodePool, Order, Product
from app.routes.admin import verify_admin

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin/store", tags=["商店管理"])


# ── Helpers ──

def _gen_code(length=16) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _auto_reply(product: Product, code: str) -> str:
    return product.reply_template.format(
        name=product.name,
        code=code,
        price=product.price,
        instructions=product.instructions,
    )


# ── Dashboard ──

@router.get("", response_class=HTMLResponse, include_in_schema=False)
def store_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    total_products = db.query(func.count(Product.id)).filter(Product.status == "active").scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    pending_orders = db.query(func.count(Order.id)).filter(Order.status == "pending").scalar()
    completed_orders = db.query(func.count(Order.id)).filter(Order.status == "completed").scalar()
    total_codes = db.query(func.count(CodePool.id)).scalar()
    unused_codes = db.query(func.count(CodePool.id)).filter(CodePool.status == "unused").scalar()

    # 最近5笔待处理订单
    recent_orders = (
        db.query(Order)
        .filter(Order.status == "pending")
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    # 今日成交
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = (
        db.query(func.coalesce(func.sum(Order.amount), 0))
        .filter(Order.status == "completed", Order.completed_at >= today_start)
        .scalar()
    )

    return templates.TemplateResponse(
        request,
        "admin/store/dashboard.html",
        {
            "total_products": total_products,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_codes": total_codes,
            "unused_codes": unused_codes,
            "recent_orders": recent_orders,
            "today_revenue": today_revenue,
            "active_page": "store",
        },
    )


# ══════════════════════════════════════════
# Products
# ══════════════════════════════════════════

@router.get("/products", response_class=HTMLResponse, include_in_schema=False)
def list_products(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    products = db.query(Product).order_by(Product.sort_order, Product.created_at.desc()).all()

    # 补充统计
    product_list = []
    for p in products:
        code_count = db.query(func.count(CodePool.id)).filter(CodePool.product_id == p.id).scalar()
        unused_count = (
            db.query(func.count(CodePool.id))
            .filter(CodePool.product_id == p.id, CodePool.status == "unused")
            .scalar()
        )
        product_list.append({**{k: getattr(p, k) for k in (
            "id", "name", "description", "price", "category",
            "stock_type", "status", "sort_order", "created_at",
            "reply_template", "instructions",
        )}, "code_count": code_count, "unused_count": unused_count})

    return templates.TemplateResponse(
        request,
        "admin/store/products.html",
        {"products": product_list, "active_page": "store"},
    )


@router.post("/products/new", include_in_schema=False)
def create_product(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form("其他"),
    description: str = Form(""),
    stock_type: str = Form("limited"),
    reply_template: str = Form(""),
    instructions: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    if not reply_template:
        reply_template = "【{name}】已发货！你的兑换码：{code}\n使用说明：请复制兑换码到 App 内输入即可激活。"

    product = Product(
        name=name,
        price=price,
        category=category,
        description=description,
        stock_type=stock_type,
        reply_template=reply_template,
        instructions=instructions,
    )
    db.add(product)
    db.commit()
    return RedirectResponse(url="/admin/store/products", status_code=303)


@router.post("/products/{product_id}/edit", include_in_schema=False)
def edit_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form("其他"),
    description: str = Form(""),
    stock_type: str = Form("limited"),
    status: str = Form("active"),
    reply_template: str = Form(""),
    instructions: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    product.name = name
    product.price = price
    product.category = category
    product.description = description
    product.stock_type = stock_type
    product.status = status
    product.instructions = instructions
    if reply_template:
        product.reply_template = reply_template
    db.commit()
    return RedirectResponse(url="/admin/store/products", status_code=303)


@router.post("/products/{product_id}/toggle", include_in_schema=False)
def toggle_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.status = "inactive" if product.status == "active" else "active"
        db.commit()
    return RedirectResponse(url="/admin/store/products", status_code=303)


# ══════════════════════════════════════════
# Code Pool
# ══════════════════════════════════════════

@router.get("/codes", response_class=HTMLResponse, include_in_schema=False)
def list_codes(
    request: Request,
    product_id: int = Query(None),
    status_filter: str = Query("all"),
    page: int = Query(1),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    per_page = 50
    query = db.query(CodePool).order_by(CodePool.created_at.desc())

    if product_id:
        query = query.filter(CodePool.product_id == product_id)
    if status_filter in ("unused", "used", "expired"):
        query = query.filter(CodePool.status == status_filter)

    total = query.count()
    codes = query.offset((page - 1) * per_page).limit(per_page).all()

    products = db.query(Product).order_by(Product.sort_order).all()

    return templates.TemplateResponse(
        request,
        "admin/store/codes.html",
        {
            "codes": codes,
            "total": total,
            "page": page,
            "per_page": per_page,
            "product_id": product_id,
            "status_filter": status_filter,
            "products": products,
            "active_page": "store",
        },
    )


@router.post("/codes/generate", include_in_schema=False)
def generate_codes(
    request: Request,
    product_id: int = Form(...),
    count: int = Form(10),
    length: int = Form(16),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    new_codes = []
    # 避免重复生成
    existing = {c.code_value for c in db.query(CodePool.code_value).filter(CodePool.product_id == product_id).all()}
    generated = 0
    attempts = 0
    while generated < count and attempts < count * 5:
        code_val = _gen_code(length)
        if code_val not in existing:
            new_codes.append(CodePool(product_id=product_id, code_value=code_val))
            existing.add(code_val)
            generated += 1
        attempts += 1

    if new_codes:
        db.bulk_save_objects(new_codes)
        db.commit()

    return RedirectResponse(
        url=f"/admin/store/codes?product_id={product_id}",
        status_code=303,
    )


@router.post("/codes/import", include_in_schema=False)
def import_codes(
    request: Request,
    product_id: int = Form(...),
    codes_text: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    lines = [l.strip() for l in codes_text.strip().split("\n") if l.strip()]
    existing = {c.code_value for c in db.query(CodePool.code_value).filter(CodePool.product_id == product_id).all()}

    new_codes = []
    for code_val in lines:
        if code_val not in existing:
            new_codes.append(CodePool(product_id=product_id, code_value=code_val))
            existing.add(code_val)

    if new_codes:
        db.bulk_save_objects(new_codes)
        db.commit()

    return RedirectResponse(
        url=f"/admin/store/codes?product_id={product_id}",
        status_code=303,
    )


# ══════════════════════════════════════════
# Orders
# ══════════════════════════════════════════

@router.get("/orders", response_class=HTMLResponse, include_in_schema=False)
def list_orders(
    request: Request,
    status_filter: str = Query("all"),
    page: int = Query(1),
    q: str = Query(""),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    per_page = 30
    query = db.query(Order).order_by(
        # pending 排最前
        Order.status == "pending",
        Order.created_at.desc(),
    )

    if status_filter in ("pending", "completed", "cancelled", "refunded"):
        query = query.filter(Order.status == status_filter)

    if q:
        query = query.filter(
            Order.platform_username.contains(q)
            | Order.platform.contains(q)
            | Order.customer_contact.contains(q)
        )

    total = query.count()
    orders = query.offset((page - 1) * per_page).limit(per_page).all()

    order_list = []
    for o in orders:
        product = db.query(Product).filter(Product.id == o.product_id).first()
        code_obj = None
        if o.assigned_code_id:
            code_obj = db.query(CodePool).filter(CodePool.id == o.assigned_code_id).first()
        order_list.append({
            "id": o.id,
            "product_name": product.name if product else "(已删除)",
            "platform": o.platform,
            "platform_username": o.platform_username,
            "customer_contact": o.customer_contact,
            "amount": o.amount,
            "status": o.status,
            "assigned_code": code_obj.code_value if code_obj else "",
            "admin_note": o.admin_note,
            "reply_text": o.reply_text,
            "created_at": o.created_at,
            "completed_at": o.completed_at,
        })

    return templates.TemplateResponse(
        request,
        "admin/store/orders.html",
        {
            "orders": order_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "status_filter": status_filter,
            "q": q,
            "active_page": "store",
        },
    )


@router.get("/orders/new", response_class=HTMLResponse, include_in_schema=False)
def new_order_page(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    products = db.query(Product).filter(Product.status == "active").order_by(Product.sort_order).all()
    return templates.TemplateResponse(
        request,
        "admin/store/order_new.html",
        {"products": products, "active_page": "store"},
    )


@router.post("/orders/new", include_in_schema=False)
def create_order(
    request: Request,
    product_id: int = Form(...),
    platform: str = Form("微信"),
    platform_username: str = Form(""),
    amount: float = Form(...),
    customer_contact: str = Form(""),
    admin_note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    order = Order(
        product_id=product_id,
        platform=platform,
        platform_username=platform_username,
        amount=amount,
        customer_contact=customer_contact,
        admin_note=admin_note,
        status="pending",
    )
    db.add(order)
    db.commit()
    return RedirectResponse(url="/admin/store/orders", status_code=303)


@router.get("/orders/{order_id}", response_class=HTMLResponse, include_in_schema=False)
def order_detail(request: Request, order_id: int, db: Session = Depends(get_db)):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    product = db.query(Product).filter(Product.id == order.product_id).first()
    code_obj = None
    if order.assigned_code_id:
        code_obj = db.query(CodePool).filter(CodePool.id == order.assigned_code_id).first()

    return templates.TemplateResponse(
        request,
        "admin/store/order_detail.html",
        {
            "order": order,
            "product": product,
            "code_obj": code_obj,
            "active_page": "store",
        },
    )


@router.post("/orders/{order_id}/confirm", include_in_schema=False)
def confirm_order(request: Request, order_id: int, db: Session = Depends(get_db)):
    """确认收款 → 自动分配码 → 生成回复话术"""
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待处理的订单可以确认")

    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=400, detail="商品不存在")

    # 分配码
    if product.stock_type == "limited":
        code_obj = (
            db.query(CodePool)
            .filter(CodePool.product_id == product.id, CodePool.status == "unused")
            .order_by(CodePool.id)
            .first()
        )
        if not code_obj:
            raise HTTPException(status_code=400, detail="库存不足！请先生成兑换码")
        code_obj.status = "used"
        code_obj.used_at = datetime.now()
        code_obj.order_id = order.id
        order.assigned_code_id = code_obj.id
        code_value = code_obj.code_value
    else:
        # 无限库存：动态生成唯一码
        code_value = _gen_code()
        code_obj = CodePool(
            product_id=product.id,
            code_value=code_value,
            status="used",
            order_id=order.id,
            used_at=datetime.now(),
        )
        db.add(code_obj)
        db.flush()
        order.assigned_code_id = code_obj.id

    # 生成回复话术
    order.reply_text = _auto_reply(product, code_value)
    order.status = "completed"
    order.completed_at = datetime.now()
    db.commit()

    return RedirectResponse(url=f"/admin/store/orders/{order.id}", status_code=303)


@router.post("/orders/{order_id}/cancel", include_in_schema=False)
def cancel_order(
    request: Request,
    order_id: int,
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        verify_admin(request)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=303)

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待处理的订单可以取消")

    order.status = "cancelled"
    if reason:
        order.admin_note = (order.admin_note + "\n" if order.admin_note else "") + f"取消原因：{reason}"
    db.commit()
    return RedirectResponse(url="/admin/store/orders", status_code=303)
