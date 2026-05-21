import json
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    pet_type = Column(String(16), nullable=False)
    nickname = Column(String(32), default="")
    intimacy = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)
    unlocked_forms = Column(Text, default=json.dumps(["baby"]))
    current_form = Column(String(16), default="baby")
    accessories = Column(Text, default=json.dumps([]))
    created_at = Column(DateTime, default=datetime.now)
    last_fed_at = Column(DateTime, nullable=True)
    last_active_at = Column(Date, nullable=True)
    last_pet_date = Column(Date, nullable=True)  # 上次抚摸日期
    last_walk_date = Column(Date, nullable=True)  # 上次散步日期


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    item_type = Column(String(20), nullable=False)
    item_id = Column(String(32), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


class PetDailyLog(Base):
    __tablename__ = "pet_daily_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False)
    pet_type = Column(String(16), nullable=False)
    shards_reward = Column(Integer, default=0)
    exp_reward = Column(Integer, default=0)
    tickets_reward = Column(Integer, default=0)
    created_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)


# 每日道具使用记录（每用户每天限制）
class ItemDailyUsage(Base):
    __tablename__ = "item_daily_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(32), nullable=False)
    use_date = Column(Date, nullable=False, index=True)
    use_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


# ===== 宠物稀有度 =====
PET_RARITY = {
    # SSR (4阶)
    "star_fox":   "SSR",
    "bamboo_dragon": "SSR",
    "wave_cat":   "SSR",
    "honey_bear": "SSR",
    # SR (3阶)
    "dream_rabbit": "SR",
    "snow_deer":  "SR",
    # R (2阶)
    "sugar_squirrel": "R",
    "lava_tanuki": "R",
    "leaf_roll":  "R",
    "paper_crane":"R",
    "wind_bell":  "R",
}

# ===== 宠物被动技能配置 =====
PASSIVE_SKILLS = {
    "star_fox":   {"name": "星尘收集✨", "desc": "收集星尘，带回积分",
        "rewards": {(60,79): {"shards":3,"exp":0,"tickets":0}, (80,99): {"shards":5,"exp":0,"tickets":0}, (100,100): {"shards":8,"exp":0,"tickets":0}}},
    "bamboo_dragon": {"name": "竹灵祝福🎋", "desc": "竹叶轻摇，有机会带回抽卡券",
        "rewards": {(60,79): {"shards":0,"exp":0,"tickets_pct":5}, (80,99): {"shards":0,"exp":0,"tickets_pct":8}, (100,100): {"shards":0,"exp":0,"tickets_pct":12}}},
    "wave_cat":   {"name": "潮汐宝藏🌊", "desc": "潮起潮落，带回大量积分",
        "rewards": {(60,79): {"shards":5,"exp":0,"tickets":0}, (80,99): {"shards":8,"exp":0,"tickets":0}, (100,100): {"shards":12,"exp":0,"tickets":0}}},
    "honey_bear": {"name": "甜蜜分享🍯", "desc": "分享甜蜜，带回经验",
        "rewards": {(60,79): {"shards":0,"exp":3,"tickets":0}, (80,99): {"shards":0,"exp":5,"tickets":0}, (100,100): {"shards":0,"exp":8,"tickets":0}}},
    "snow_deer":  {"name": "冰雪馈赠❄️", "desc": "冰雪祝福，带回积分和抽卡券",
        "rewards": {(60,79): {"shards":3,"exp":0,"tickets_pct":3}, (80,99): {"shards":5,"exp":0,"tickets_pct":5}, (100,100): {"shards":10,"exp":0,"tickets_pct":8}}},
    "dream_rabbit": {"name": "梦幻花粉🌸", "desc": "抖落花粉，带回经验",
        "rewards": {(60,79): {"shards":0,"exp":2,"tickets":0}, (80,99): {"shards":0,"exp":4,"tickets":0}, (100,100): {"shards":0,"exp":6,"tickets":0}}},
    "wind_bell":  {"name": "风铃清音🎐", "desc": "清风吹拂，带回积分",
        "rewards": {(60,79): {"shards":2,"exp":0,"tickets":0}, (80,99): {"shards":3,"exp":0,"tickets":0}, (100,100): {"shards":5,"exp":0,"tickets":0}}},
    "sugar_squirrel": {"name": "栗子投喂🌰", "desc": "找到栗子，带回积分",
        "rewards": {(60,79): {"shards":2,"exp":0,"tickets":0}, (80,99): {"shards":3,"exp":0,"tickets":0}, (100,100): {"shards":4,"exp":0,"tickets":0}}},
    "lava_tanuki": {"name": "余温暖暖🔥", "desc": "暖意洋洋，带回经验",
        "rewards": {(60,79): {"shards":0,"exp":2,"tickets":0}, (80,99): {"shards":0,"exp":3,"tickets":0}, (100,100): {"shards":0,"exp":4,"tickets":0}}},
    "leaf_roll":  {"name": "叶卷藏宝🍃", "desc": "叶子卷着宝贝回来",
        "rewards": {(60,79): {"shards":1,"exp":0,"tickets":0}, (80,99): {"shards":2,"exp":0,"tickets":0}, (100,100): {"shards":3,"exp":0,"tickets":0}}},
    "paper_crane": {"name": "纸鹤传信✉️", "desc": "衔来小礼物",
        "rewards": {(60,79): {"shards":0,"exp":1,"tickets":0}, (80,99): {"shards":0,"exp":2,"tickets":0}, (100,100): {"shards":0,"exp":3,"tickets":0}}},
}

def get_passive_reward(pet_type: str, intimacy: int) -> dict:
    skill = PASSIVE_SKILLS.get(pet_type)
    if not skill:
        return {"shards": 0, "exp": 0, "tickets": 0}
    rewards_cfg = skill["rewards"]
    matched = None
    for (lo, hi), cfg in sorted(rewards_cfg.items(), key=lambda x: x[0][0]):
        if lo <= intimacy <= hi:
            matched = cfg
            break
    if not matched:
        return {"shards": 0, "exp": 0, "tickets": 0}
    result = {"shards": matched.get("shards", 0), "exp": matched.get("exp", 0), "tickets": 0}
    pct = matched.get("tickets_pct", 0)
    if pct > 0:
        import random
        if random.random() * 100 < pct:
            result["tickets"] = 1
    return result


# ===== 宠物配置 =====

PET_EMOJI = {
    # SSR
    "star_fox":    {"baby":"🦊", "teen":"🦊🌟", "adult":"🦊✨", "deluxe":"🦊🌌", "legend":"🦊🌀"},
    "bamboo_dragon":{"baby":"🐉", "teen":"🐉🎋", "adult":"🐉🌿", "deluxe":"🐉⚔️", "legend":"🐉🗡️"},
    "wave_cat":    {"baby":"🐱", "teen":"🐱🌊", "adult":"🐱🐚", "deluxe":"🐱🧜", "legend":"🐱👑"},
    "honey_bear":  {"baby":"🐻", "teen":"🐻🍩", "adult":"🐻🍰", "deluxe":"🐻👑", "legend":"🐻🎂"},
    "snow_deer":   {"baby":"🦌", "teen":"🦌❄️", "adult":"🦌🌨️", "deluxe":"🦌🧊", "legend":"🦌💎"},
    # SR
    "dream_rabbit":{"baby":"🐰", "teen":"🐰🌸", "adult":"🐰🦋"},
    "wind_bell":   {"baby":"🔔", "teen":"🌸🔔", "adult":"🧚🎐"},
    # R
    "sugar_squirrel":{"baby":"🐿️", "teen":"🐿️🌰"},
    "lava_tanuki":   {"baby":"🦝", "teen":"🦝🔥"},
    "leaf_roll":     {"baby":"🍃", "teen":"🍃🌿"},
    "paper_crane":   {"baby":"🕊️", "teen":"🦢🌈"},
}

FORM_NAMES = {
    # SSR (4阶)
    "star_fox":    ["星绒狐", "星辉狐", "星云狐", "星河神狐"],
    "bamboo_dragon":["嫩芽龙", "青竹龙", "竹灵龙", "九节神竹龙"],
    "wave_cat":    ["浪花喵", "潮汐喵", "珊瑚喵", "海神喵"],
    "honey_bear":  ["棉花糖熊", "甜甜圈熊", "蜜糖蛋糕熊", "糖果女王熊"],
    "snow_deer":   ["雪团鹿", "霜角鹿", "暴风雪鹿"],
    # SR (3阶)
    "dream_rabbit":["绒耳兔", "花铃兔", "蝶翼兔"],
    "wind_bell":   ["风铃芽", "花铃仙"],
    # R (2阶)
    "sugar_squirrel":["橡果鼠", "糖栗鼠"],
    "lava_tanuki":   ["暖炭狸", "熔岩狸"],
    "leaf_roll":     ["叶卷卷", "卷叶蛹"],
    "paper_crane":   ["小纸鹤", "千纸鹤"],
}

FORM_THRESHOLDS = {
    "baby": 0,
    "teen": 1000,
    "adult": 5000,
    "deluxe": 20000,
    "legend": 100000,
}

EVOLUTION_ITEMS = {
    # SSR 进化道具（4阶→传说）
    "star_ribbon":   {"pet": "star_fox", "form": "legend", "form_label": "星河绶带🌀"},
    "bamboo_sword":  {"pet": "bamboo_dragon", "form": "legend", "form_label": "青竹剑🗡️"},
    "sea_crown":     {"pet": "wave_cat", "form": "legend", "form_label": "神海王冠👑"},
    "rainbow_cape":  {"pet": "honey_bear", "form": "deluxe", "form_label": "彩虹披风🎂"},
}
