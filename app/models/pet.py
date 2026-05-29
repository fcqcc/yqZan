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
    today_interact_count = Column(Integer, default=0)  # 今日互动计数器
    last_interact_date = Column(Date, nullable=True)  # 计数器对应的日期
    exp = Column(Integer, default=0)  # 当前经验值
    level = Column(Integer, default=1)  # 当前等级
    evolution_ready = Column(Boolean, default=False)  # 是否可进化


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
    # SSR (4阶：baby/teen/adult/final)
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

# ===== 经验值配置 =====
# 每升一级需要4点经验（恒定）
EXP_PER_LEVEL = 4
# 各稀有度绝对最大等级（不可超过）
MAX_LEVEL = {"SSR": 20, "SR": 15, "R": 10}
# 每日交互经验上限(互动+存款+目标)
DAILY_DEPOSIT_EXP_LIMIT = 3  # 每日存款可获经验次数
DAILY_GOAL_EXP_LIMIT = 2     # 每日达成目标可获经验次数

# 根据等级决定形态: 每5级解锁一阶
def get_form_by_level(level):
    if level >= 20: return "legend"
    if level >= 15: return "deluxe"
    if level >= 10: return "adult"
    if level >= 5:  return "teen"
    return "baby"

def get_current_level_cap(pet) -> int:
    """获取当前进化形态下的等级上限（动态递增）
    
    每解锁一个基础形态，上限+5：
    - baby (0次进化): cap=5
    - teen  (1次进化): cap=10
    - adult (2次进化): cap=15
    - deluxe(3次进化): cap=20
    同时受稀有度绝对上限限制（R:10, SR:15, SSR:20）
    """
    import json
    unlocked = json.loads(pet.unlocked_forms) if isinstance(pet.unlocked_forms, str) else pet.unlocked_forms
    base_forms = [f for f in ["baby", "teen", "adult", "deluxe", "legend"] if f in unlocked]
    stage_cap = 5 * len(base_forms)
    rarity = PET_RARITY.get(pet.pet_type, "R")
    return min(stage_cap, MAX_LEVEL.get(rarity, 10))

EVOLUTION_ITEMS = {

    # SSR 进化道具（4阶→最终形态）
    "star_ribbon":   {"pet": "star_fox", "form": "deluxe", "form_label": "星河绶带🌀", "display_emoji": "🌀"},
    "bamboo_sword":  {"pet": "bamboo_dragon", "form": "deluxe", "form_label": "青竹剑🗡️", "display_emoji": "🗡️"},
    "sea_crown":     {"pet": "wave_cat", "form": "deluxe", "form_label": "神海王冠👑", "display_emoji": "👑"},
    "rainbow_cape":  {"pet": "honey_bear", "form": "deluxe", "form_label": "彩虹披风🎂", "display_emoji": "🎂"},
}
