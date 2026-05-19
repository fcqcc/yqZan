import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    pet_type = Column(String(16), nullable=False)  # pig / fox / cat / unicorn / dragon
    nickname = Column(String(32), default="")
    intimacy = Column(Integer, default=0)  # 0-100
    is_active = Column(Boolean, default=False)
    unlocked_forms = Column(Text, default=json.dumps(["baby"]))  # JSON list
    current_form = Column(String(16), default="baby")
    accessories = Column(Text, default=json.dumps([]))  # JSON list of accessory ids
    created_at = Column(DateTime, default=datetime.now)
    last_fed_at = Column(DateTime, nullable=True)  # 最近一次喂食时间


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    item_type = Column(String(20), nullable=False)  # pet/accessory/background/evolution_item/consumable
    item_id = Column(String(32), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


# ===== 宠物配置（写死在代码里的常量，不存数据库） =====

# 每种宠物的 emoji（按形态排列）
PET_EMOJI = {
    "pig":    {"baby": "🐷", "teen": "🐽", "adult": "🐖", "deluxe": "🐗", "legend": "🐷✨"},
    "fox":    {"baby": "🦊", "teen": "🦊", "adult": "🦊🔥", "deluxe": "🦊🌙", "legend": "🦊🌌"},
    "cat":    {"baby": "🐱", "teen": "🐱", "adult": "🐱💰", "deluxe": "🐱🗾", "legend": "🐱🤖"},
    "unicorn": {"baby": "🦄", "teen": "🦄🌈", "adult": "🦄✨", "deluxe": "🦄💫", "legend": "🦄🌠"},
    "dragon": {"baby": "🐉", "teen": "🐉🔥", "adult": "🐉⭐", "deluxe": "🐉👑", "legend": "🐉🌌"},
}

# 形态标签（中文名）
FORM_NAMES = {
    "pig":    ["小粉猪", "中猪", "金猪", "财神猪", "聚宝猪"],
    "fox":    ["小狐狸", "银狐", "九尾狐", "月狐", "星河狐"],
    "cat":    ["小奶猫", "招财猫", "金招财", "达摩猫", "机械猫"],
    "unicorn": ["小独角兽", "彩虹兽", "星光兽", "幻光兽", "天马"],
    "dragon": ["小龙", "火龙", "辰龙", "金龙", "神龙"],
}

# 按总存款解锁的形态门槛
FORM_THRESHOLDS = {
    "baby": 0,
    "teen": 1000,
    "adult": 5000,
    "deluxe": 20000,
    "legend": 100000,
}

# 进化道具 → 对应宠物 + 分支形态
EVOLUTION_ITEMS = {
    "gold_ingot":   {"pet": "pig", "form": "deluxe", "form_label": "招财进宝🧧", "display_emoji": "🐷🧧"},
    "love_arrow":   {"pet": "pig", "form": "deluxe", "form_label": "爱心猪💕", "display_emoji": "🐷💕"},
    "mech_core":    {"pet": "pig", "form": "legend", "form_label": "赛博猪🤖", "display_emoji": "🐷🤖"},
    "moon_stone":   {"pet": "fox", "form": "deluxe", "form_label": "月狐🌙", "display_emoji": "🦊🌙"},
    "stardust":     {"pet": "fox", "form": "legend", "form_label": "星河狐🌌", "display_emoji": "🦊🌌"},
    "fortune_bell": {"pet": "cat", "form": "deluxe", "form_label": "达摩猫🗾", "display_emoji": "🐱🗾"},
}
