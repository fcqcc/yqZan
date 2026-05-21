# 成就配置：成就ID → 名称/条件描述/奖励类型/奖励数量/隐藏
ACHIEVEMENTS = {
    # === 打卡坚持类（积分奖励） ===
    "streak_3": {
        "name": "持之以恒·3🔥",
        "desc": "连续签到3天",
        "reward_type": "shards", "reward_amount": 20,
        "hidden": False, "category": "打卡",
    },
    "streak_5": {
        "name": "持之以恒·5🔥🔥",
        "desc": "连续签到5天",
        "reward_type": "shards", "reward_amount": 30,
        "hidden": False, "category": "打卡",
    },
    "streak_7": {
        "name": "持之以恒·7🔥🔥🔥",
        "desc": "连续签到7天",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "打卡",
    },
    "streak_10": {
        "name": "持之以恒·10🔥🔥🔥🔥",
        "desc": "连续签到10天",
        "reward_type": "shards", "reward_amount": 80,
        "hidden": False, "category": "打卡",
    },
    "streak_14": {
        "name": "持之以恒·14🔥🔥🔥🔥🔥",
        "desc": "连续签到14天",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "打卡",
    },
    "streak_21": {
        "name": "持之以恒·21🔥🔥🔥🔥🔥🔥",
        "desc": "连续签到21天",
        "reward_type": "shards", "reward_amount": 150,
        "hidden": False, "category": "打卡",
    },
    "streak_30": {
        "name": "持之以恒·30🔥🔥🔥🔥🔥🔥🔥",
        "desc": "连续签到30天",
        "reward_type": "shards", "reward_amount": 200,
        "hidden": False, "category": "打卡",
    },
    "streak_45": {
        "name": "持之以恒·45🔥🔥🔥🔥🔥🔥🔥🔥",
        "desc": "连续签到45天",
        "reward_type": "shards", "reward_amount": 300,
        "hidden": False, "category": "打卡",
    },
    "streak_60": {
        "name": "持之以恒·60🔥🔥🔥🔥🔥🔥🔥🔥🔥",
        "desc": "连续签到60天",
        "reward_type": "shards", "reward_amount": 400,
        "hidden": False, "category": "打卡",
    },
    "streak_100": {
        "name": "持之以恒·100🔥👑",
        "desc": "连续签到100天",
        "reward_type": "shards", "reward_amount": 500,
        "hidden": False, "category": "打卡",
    },
    # === 里程碑类（积分奖励）===
    "first_open": {
        "name": "这是哪？👋",
        "desc": "第一次打开应用",
        "reward_type": "shards", "reward_amount": 10,
        "hidden": False, "category": "里程碑",
    },
    "first_deposit": {
        "name": "财富自由的开始💰",
        "desc": "存入第一笔钱",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "里程碑",
    },
    "first_goal": {
        "name": "完成第一个目标🎯",
        "desc": "完成第一个存钱目标",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "里程碑",
    },
    "first_bind": {
        "name": "成功邀请对象💑",
        "desc": "成功绑定伴侣",
        "reward_type": "shards", "reward_amount": 80,
        "hidden": False, "category": "里程碑",
    },
    # === 宠物类（积分奖励） ===
    "first_pet": {
        "name": "你好小来福🐾",
        "desc": "获得第一只宠物",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "宠物",
    },
    "first_form": {
        "name": "成长蜕变🦋",
        "desc": "解锁第一个新形态",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "宠物",
    },
    "first_evolve": {
        "name": "进化✨",
        "desc": "首次使用进化道具",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "宠物",
    },
    "legend_form": {
        "name": "给我变🌟",
        "desc": "一只宠物达到传说形态",
        "reward_type": "shards", "reward_amount": 200,
        "hidden": False, "category": "宠物",
    },
    "max_intimacy": {
        "name": "心有灵犀💕",
        "desc": "亲密度达到100",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "宠物",
    },
    "all_pets": {
        "name": "宠物收藏家🐱",
        "desc": "拥有全部5种宠物",
        "reward_type": "shards", "reward_amount": 500,
        "hidden": False, "category": "宠物",
    },
    # === 抽卡类（积分奖励）===
    "gacha_10": {
        "name": "初次尝试🎰",
        "desc": "抽卡10次",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "抽卡",
    },
    "gacha_100": {
        "name": "抽卡达人🎰🎰",
        "desc": "抽卡100次",
        "reward_type": "shards", "reward_amount": 200,
        "hidden": False, "category": "抽卡",
    },
    "gacha_1000": {
        "name": "扭蛋之王🎰👑",
        "desc": "抽卡1,000次",
        "reward_type": "shards", "reward_amount": 500,
        "hidden": False, "category": "抽卡",
    },
    # === 隐藏成就（抽卡券奖励） ===
    "golden_legend": {
        "name": "金色传说✨",
        "desc": "抽到传说级宠物",
        "reward_type": "tickets", "reward_amount": 20,
        "hidden": True, "category": "隐藏",
    },
    "first_ssrp": {
        "name": "天选之人🌟",
        "desc": "抽到SSR+",
        "reward_type": "tickets", "reward_amount": 30,
        "hidden": True, "category": "隐藏",
    },
    "all_pets_collected": {
        "name": "全图鉴收集🏆",
        "desc": "集齐所有宠物",
        "reward_type": "tickets", "reward_amount": 50,
        "hidden": True, "category": "隐藏",
    },
    "streak_recover": {
        "name": "重燃火花🔥",
        "desc": "火花从置灰恢复",
        "reward_type": "tickets", "reward_amount": 5,
        "hidden": True, "category": "隐藏",
    },
    # === 新增：亲密度维持类 ===
    "intimacy_keep_7d": {
        "name": "宠辱不惊💕",
        "desc": "亲密度100维持7天",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "宠物",
    },
    "all_pets_intimacy_60": {
        "name": "宠物大家长👨‍👩‍👧‍👦",
        "desc": "所有宠物亲密度均达到60以上",
        "reward_type": "shards", "reward_amount": 200,
        "hidden": False, "category": "宠物",
    },
    # === 新增：冒险类 ===
    "adventure_7d": {
        "name": "探索达人🗺️",
        "desc": "连续7天触发宠物冒险",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "宠物",
    },
    # === 新增：抽卡类 ===
    "gacha_boost": {
        "name": "豪赌一把🎲",
        "desc": "首次使用积分加注抽卡",
        "reward_type": "shards", "reward_amount": 50,
        "hidden": False, "category": "抽卡",
    },
    "gacha_pity": {
        "name": "非酋的救赎🛡️",
        "desc": "触发低保机制（30抽无SSR+）",
        "reward_type": "shards", "reward_amount": 80,
        "hidden": True, "category": "隐藏",
    },
    # === 新增：等级类 ===
    "level_10": {
        "name": "初出茅庐🌟",
        "desc": "情侣等级达到10级",
        "reward_type": "shards", "reward_amount": 100,
        "hidden": False, "category": "里程碑",
    },
    "level_30": {
        "name": "情比金坚💎",
        "desc": "情侣等级达到30级",
        "reward_type": "shards", "reward_amount": 300,
        "hidden": False, "category": "里程碑",
    },
    # === 新增：火花类 ===
    "spark_7": {
        "name": "火花守护·7🔥",
        "desc": "连续7天火花保持活跃",
        "reward_type": "shards", "reward_amount": 30,
        "hidden": False, "category": "打卡",
    },
    "spark_30": {
        "name": "火花守护·30🔥",
        "desc": "连续30天火花保持活跃",
        "reward_type": "shards", "reward_amount": 150,
        "hidden": False, "category": "打卡",
    },
}
