from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.models.card import CardTemplate
from app.jinja_fix import *  # Must come before other imports that use Jinja2
from app.routes import admin_router, card_router, couple_router, extra_router, plan_router, social_router, user_router


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


app = FastAPI(title="Couple Promise API", version="0.1.0")


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


@app.get("/health")
def health():
    return {"status": "ok"}
