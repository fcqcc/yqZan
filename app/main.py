from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, SessionLocal
from app.models.card import CardTemplate
from app.models.social import TaskEvent
from app.jinja_fix import *  # Must come before other imports that use Jinja2
from app.routes import achievement_router, admin_router, card_router, card_task_router, checkin_router, couple_router, draw_router, extra_router, gacha_router, pet_router, plan_router, social_router, user_router


PRESET_TEMPLATES = [
    {"name": "简约告白", "type": "template", "description": "简洁文字+背景，适合日常发送",
     "style_config": '{"bg":"linear-gradient(135deg,#ffecd2,#fcb69f)","font":"serif","accent":"#d4380d"}',
     "min_level": 1, "sort_order": 1},
    {"name": "浪漫之约", "type": "template", "description": "玫瑰金配色，适合纪念日",
     "style_config": '{"bg":"linear-gradient(135deg,#fce4ec,#e8a0bf)","font":"serif","accent":"#ad1457"}',
     "min_level": 1, "sort_order": 2},
    {"name": "星空物语", "type": "template", "description": "深蓝星空，适合跨年/生日",
     "style_config": '{"bg":"linear-gradient(135deg,#0d1b2a,#1b3a5c)","font":"sans","accent":"#ffd54f"}',
     "min_level": 3, "sort_order": 3},
    {"name": "年度总结", "type": "flip", "description": "翻页书效果，汇总全年数据",
     "style_config": '{"bg":"linear-gradient(160deg,#221018,#9d2d5a)","font":"serif","accent":"#c9a227","pages":true}',
     "min_level": 1, "sort_order": 10},
    {"name": "纪念日快乐", "type": "auto", "description": "纪念日自动生成",
     "style_config": '{"bg":"linear-gradient(135deg,#fce4ec,#f8bbd0)","font":"serif","accent":"#c62828"}',
     "min_level": 1, "sort_order": 20},
    {"name": "目标达成", "type": "auto", "description": "存钱目标达成时自动生成",
     "style_config": '{"bg":"linear-gradient(135deg,#e8f5e9,#a5d6a7)","font":"sans","accent":"#2e7d32"}',
     "min_level": 1, "sort_order": 21},
]

TASK_EVENTS = [
    {"event_code": "heart_photo", "title": "比心合照", "description": "一起拍一张比心合照，记录你们的甜蜜时刻",
     "exp_reward": 80, "category": "romance", "icon": "📸"},
    {"event_code": "cook_together", "title": "一起做饭", "description": "一起做一顿饭，从买菜到洗碗全程合作",
     "exp_reward": 50, "category": "life", "icon": "🍳"},
    {"event_code": "sunrise_date", "title": "一起看日出", "description": "早起一起看一次日出，拍照留念",
     "exp_reward": 60, "category": "romance", "icon": "🌅"},
    {"event_code": "workout_week", "title": "一起运动一周", "description": "连续7天一起运动，互相督促",
     "exp_reward": 100, "category": "sport", "icon": "💪"},
    {"event_code": "letter_to_you", "title": "写一封情书", "description": "手写一封情书送给对方，拍照上传",
     "exp_reward": 70, "category": "romance", "icon": "💌"},
    {"event_code": "study_session", "title": "一起学习3小时", "description": "一起专注学习/工作3小时，互相监督",
     "exp_reward": 40, "category": "study", "icon": "📚"},
]


app = FastAPI(title="Couple Promise API", version="0.1.0")


# ===== 统一错误处理 =====

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """422 参数验证 → 提取第一条可读错误"""
    errors = exc.errors()
    if errors:
        first = errors[0]
        msg = first.get("msg", "")
        loc = ".".join(str(x) for x in first.get("loc", [])) if first.get("loc") else ""
        detail = f"参数错误: {msg}" if not loc else f"参数 {loc}: {msg}"
    else:
        detail = "请求参数错误"
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """500 未知错误 → 不暴露内部细节"""
    import traceback
    print(f"[500] {type(exc).__name__}: {exc}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # seed card templates
    db = SessionLocal()
    try:
        if db.query(CardTemplate).count() == 0:
            for t in PRESET_TEMPLATES:
                db.add(CardTemplate(**t))
            db.commit()
            print("✅ 预置贺卡模板已写入")
    finally:
        db.close()

    # seed task events
    db = SessionLocal()
    try:
        if db.query(TaskEvent).count() == 0:
            for e in TASK_EVENTS:
                db.add(TaskEvent(**e))
            db.commit()
            print("✅ 任务事件已写入")
    finally:
        db.close()


# 静态页面
#app.mount("/fortune", StaticFiles(directory="weapp/fortune", html=True), name="fortune")
# 宠物形象静态资源
import os
assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(couple_router)
app.include_router(plan_router)
app.include_router(extra_router)
app.include_router(social_router)
app.include_router(card_router)
app.include_router(admin_router)
app.include_router(achievement_router)
app.include_router(checkin_router)
app.include_router(pet_router)
app.include_router(gacha_router)
app.include_router(card_task_router)
app.include_router(draw_router)


@app.get("/health")
def health():
    return {"status": "ok"}
