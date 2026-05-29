# 一起攒 — 情侣存钱小程序 详细设计

> 版本：v0.4.1  
> 最后更新：2026-05-21  
> 技术栈：FastAPI (Python) + WeChat Mini Program + MySQL

---

## 一、整体架构

### 1.1 系统分层

```
┌──────────────────────────────────────┐
│        微信小程序前端 (weapp/)         │
│  WXML/WXSS + JS (原生框架)           │
├──────────────────────────────────────┤
│           HTTP REST API              │
├──────────────────────────────────────┤
│     FastAPI 后端 (app/)              │
│  路由层 → 服务层 → 模型层            │
├──────────────────────────────────────┤
│          MySQL 数据库                 │
│   (SQLAlchemy ORM + pymysql)         │
└──────────────────────────────────────┘
```

### 1.2 运行环境

| 组件 | 位置 | 启动方式 |
|---|---|---|
| 后端 (WSL) | `/home/root_1/workspace/couple-promise-v2/` | `python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload` |
| 数据库 | 宿主机 MySQL (172.19.16.1:3306) | Windows 服务 |
| 前端 | `F:\工作代码\couple-promise-v2\weapp\` | 微信开发者工具 |

---

## 二、数据模型

### 2.1 核心实体关系

```
User (1) ──── (N) Couple (1) ──── (N) Plan
                                  ├─── (N) Checkin
                                  ├─── (N) Pet
                                  ├─── (N) Inventory
                                  ├─── (N) Card
                                  ├─── (N) CardTask
                                  ├─── (N) Note
                                  ├─── (N) Task
                                  ├─── (N) Level
                                  ├─── (N) Anniversary
                                  ├─── (N) ToDo
                                  ├─── (N) Gift
                                  └─── (N) GameLog
```

### 2.2 用户 (User)

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | 自增主键 |
| openid | VARCHAR(64) UNIQUE | 微信 openid，登录凭证 |
| nickname | VARCHAR(32) NULL | 用户昵称，首次设置 |
| password_hash | VARCHAR(128) NULL | 密码（已废弃，保留兼容） |
| invite_code | VARCHAR(6) UNIQUE | 6位邀请码（MD5(openid)[:6]） |
| couple_id | INT FK→couples.id | 所属 Couple |
| birthday, gender | VARCHAR | 个人信息 |
| is_admin | BOOL | 管理后台标识 |
| has_nickname | property | nickname 是否已设置 |

### 2.3 情侣组 (Couple)

| 字段 | 类型 | 说明 |
|---|---|---|
| status | VARCHAR | active / archived |
| draw_tickets | INT | 抽奖券数量 |
| shards | INT | 积分（晶石） |
| spark_count | INT | 火花连续天数 |
| max_spark_count | INT | 最高火花纪录 |
| spark_status | VARCHAR | active / gray |
| gacha_pity | INT | 抽卡低保计数 |
| candy_date/count | DATE/INT | 亲密糖果使用限制 |
| deposit_exp_date/count | DATE/INT | 存款经验限制 |
| goal_exp_date/count | DATE/INT | 目标经验限制 |

### 2.4 存钱计划 (Plan)

| 字段 | 类型 | 说明 |
|---|---|---|
| title | VARCHAR | 计划名称 |
| target_amount | FLOAT | 目标金额 |
| current_amount | FLOAT | 当前金额 |
| start_date/end_date | VARCHAR | 起止日期 |
| unlimited | BOOL | 无上限计划 |
| done | BOOL | 是否完成 |
| notify_status | TEXT(JSON) | 对方读状态 |

同时有 Delivery（存入明细）和 Wish（心愿单）两个子模型。

### 2.5 宠物 (Pet)

| 字段 | 类型 | 说明 |
|---|---|---|
| pet_type | VARCHAR | star_fox / bamboo_dragon / wave_cat / honey_bear 等 |
| intimacy | INT | 亲密度 0-100 |
| is_active | BOOL | 是否活跃 |
| unlocked_forms | TEXT(JSON) | 已解锁形态列表 |
| current_form | VARCHAR | 当前形态 baby/teen/adult/deluxe/legend |
| exp | INT | 当前经验 |
| level | INT | 当前等级 |
| evolution_ready | BOOL | 是否可进化 |

**稀有度体系：**
- SSR（4阶）：star_fox, bamboo_dragon, wave_cat, honey_bear — 上限 20 级
- SR（3阶）：dream_rabbit, snow_deer — 上限 15 级
- R（2阶）：sugar_squirrel, lava_tanuki, leaf_roll, paper_crane, wind_bell, star_fluff — 上限 10 级

**形态解锁：** baby→lv5→teen→lv10→adult→item→deluxe/legend

### 2.6 背包 (Inventory)

```python
item_types: ["pet", "consumable", "evolution_item", "card", "background"]
```

详见 `app/catalog.py` — 包含切换卡、亲密糖果、火花卡、幸运饼干、经验糖果、8种卡牌、4种进化道具、2种背景。

### 2.7 其他模型

| 模型 | 说明 |
|---|---|
| Checkin | 签到记录（每人每天一条） |
| Level/LevelLog | 情侣等级经验系统 |
| Note | 便利贴（可点赞/盖章） |
| Task/TaskEvent | 情侣任务系统 |
| Card/CardTemplate | 贺卡系统（纪念日自动/手动生成） |
| CardTask | 卡片任务（使用背包卡牌触发） |
| Anniversary | 纪念日 |
| ToDo/ToDoCheckin | 待办事项 |
| Gift | 礼物记录 |
| GameLog | 游戏行为日志（进化/抽卡/道具等） |
| AchievementProgress | 成就进度追踪 |

---

## 三、API 路由总览

### 3.1 用户认证 (`/api/`)

| 方法 | 路径 | 说明 | 登录要求 |
|---|---|---|---|
| POST | `/api/wx-login` | 微信登录（code→openid→JWT） | 否 |
| POST | `/api/set-nickname` | 首次设置昵称 | 是 |
| GET | `/api/me` | 获取当前用户信息 | 是 |

### 3.2 情侣 (`/api/`)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/bind` | 绑定伴侣（邀请码） |
| POST | `/api/unbind` | 解绑伴侣 |
| GET | `/api/partner` | 获取伴侣信息 |

### 3.3 存钱计划 (`/api/plans`)

Plans CRUD + Delivery 存入 + Wish CRUD + 完成祝贺。

### 3.4 纪念日/礼物/待办 (`/api/`)

Anniversaries/Gifts/ToDos CRUD + 节假日导入。

### 3.5 社交 (`/api/`)

Notes CRUD + 点赞/盖章/邮票 + 情侣任务系统。

### 3.6 等级 (`/api/level`)

获取等级、日志、消费升级动画。

### 3.7 签到 (`/api/checkin`)

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/checkin` | 每日签到（自动） |
| GET | `/api/checkin/status` | 签到+火花状态 |
| GET | `/api/checkin/spark` | 火花详情 |

**火花规则：**
- 每天两人都签到 → 火花+1天
- 断签一天 → 火花变灰
- 变灰后连续3天签到 → 恢复
- 变灰超过3天 → 火花重置为0

### 3.8 宠物 (`/api/pets`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/pets` | 宠物列表 |
| GET | `/api/pets/active` | 获取活跃宠物（无则返回 null） |
| POST | `/api/pets/switch` | 切换活跃宠物 |
| POST | `/api/pets/{id}/feed` | 喂食（+3亲密度，每日1次） |
| POST | `/api/pets/{id}/pet` | 抚摸（+2亲密度，每日1次） |
| POST | `/api/pets/{id}/walk` | 散步（+2亲密度，每日1次） |
| POST | `/api/pets/{id}/form` | 切换形态 |
| POST | `/api/pets/{id}/evolve` | 道具进化 |
| POST | `/api/pets/{id}/level-evolve` | 等级进化 |
| GET | `/api/pets/daily-adventure` | 每日冒险（被动技能触发） |
| GET | `/api/pets/bestiary` | 宠物图鉴 |
| GET | `/api/pets/inventory` | 背包 |
| POST | `/api/pets/inventory/use` | 使用道具 |

### 3.9 抽卡 (`/api/gacha`)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/gacha/pool` | 卡池配置 |
| GET | `/api/gacha/tickets` | 抽奖券数量 |
| POST | `/api/gacha/draw` | 单抽 |
| POST | `/api/gacha/draw10` | 十连（可积分加注） |
| POST | `/api/gacha/buy-tickets` | 积分购买抽奖券 |

**概率：** SSR 宠物 1.2%、SR 进化道具 3%、SR 宠物 5%、R 宠物 10%、R 消耗品 30%、N 卡牌 35%、N 背景 15.6%

**低保：** 20抽→1.5x概率, 40抽→2x, 60抽→3x

### 3.10 贺卡 (`/api/card`)

模板管理 + 生成贺卡 + 快照数据。

### 3.11 卡片任务 (`/api/card-tasks`)

8种卡牌类型：5种家务卡/为我服务/原谅我/请原谅我（极稀有）。

状态流转：`pending → accepted → completed_pending → confirm → completed`

### 3.12 成就 (`/api/achievements`)

30+ 成就：签到连续天数、里程碑、宠物收集、抽卡次数、等级、火花等。

### 3.13 管理后台 (`/api/admin`)

用户管理、Couple 管理、数据面板。

---

## 四、前端页面结构

| 页面 | 路由 | Tab | 说明 |
|---|---|---|---|
| 登录 | pages/login/login | 否 | 微信一键登录 + 设置昵称 |
| 首页 | pages/home/home | ✅ 首页 | 伴侣信息、存钱进度、纪念日、宠物互动、快捷入口 |
| 计划 | pages/plans/plans | ✅ 计划 | 存钱计划列表+详情 |
| 我的 | pages/settings/settings | ✅ 我的 | 用户信息、伴侣绑定、功能入口 |
| 纪念日 | pages/anniversaries/anniversaries | 否 | 纪念日管理 |
| 宠物 | pages/pets/pets | 否 | 宠物管理/进化和形态切换 |
| 抽卡 | pages/gacha/gacha | 否 | 抽奖/抽宠物 |
| 背包 | pages/backpack/backpack | 否 | 物品/道具/卡牌使用 |
| 等级 | pages/level/level | 否 | 情侣等级与经验 |
| 便利贴 | pages/notes/notes | 否 | 留言板 |
| 心愿 | pages/wishes/wishes | 否 | 心愿单 |
| 待办 | pages/todos/todos | 否 | 待办事项 |
| 任务 | pages/tasks/tasks | 否 | 情侣任务 |
| 礼物 | pages/gifts/gifts | 否 | 礼物记录 |
| 贺卡 | pages/cards/cards | 否 | 贺卡查看 |

---

## 五、核心业务流程

### 5.1 用户登录流

```
打开小程序 → app.js onLaunch 检查 token
  ├─ 有 token → 直接进入首页
  └─ 无 token → 登录页
       └─ 点击"微信一键登录"
            └─ wx.login() → code
                 └─ POST /api/wx-login { code }
                      └─ wx_code_to_openid() → openid
                           └─ get_or_create_user_by_openid()
                                ├─ 已存在 → 返回 JWT
                                └─ 新建 → create Couple(5 tickets) → 返回 JWT
                 └─ 前端存 token
                      ├─ has_nickname=false → 设置昵称
                      └─ has_nickname=true → 跳转首页
```

### 5.2 伴侣绑定流

```
用户A 查看自己的邀请码 → 分享给 用户B
用户B 输入邀请码 → POST /api/bind { invite_code }
  → 校验双方无伴侣
  → 创建共享 Couple
  → 迁移两人数据到共享 Couple
  → 奖励 5 张抽奖券
```

### 5.3 存钱流程

```
创建计划 → 每次存入金额(Delivery)
  → 更新计划 current_amount
  → 触发经验（存款经验今日未超限则+）
  → 目标达成 → done=true → 自动生成贺卡
```

### 5.4 宠物养成流

```
抽卡获得宠物 → 默认 baby 形态
  → 每日喂食/抚摸/散步 → +亲密度
  → 获得经验 → 每5级进化一次
  → SSR满15级需道具进化
  → 道具进化 → deluxe/legend 形态
```

---

## 六、积分经济体系

| 行为 | 获得 | 说明 |
|---|---|---|
| 每日签到 | +5 积分 +5 EXP | 自动 |
| 伴侣双签 | +5 额外积分 | |
| 存钱 | +经验 | 每日有限额 |
| 完成目标 | +经验 | |
| 抽卡 | 消耗抽奖券 | 1券/单抽，10券/十连 |
| 积分购买券 | +1 券 / 50 积分 | |
| 成就奖励 | 积分/抽奖券 | 30+成就 |
| 宠物冒险 | 积分/经验/券 | 被动技能触发 |

---

## 七、项目文件结构

```
couple-promise-v2/
├── app/                          # FastAPI 后端
│   ├── main.py                   # 应用入口，路由注册
│   ├── config.py                 # 配置（DB/JWT/微信）
│   ├── database.py               # SQLAlchemy 引擎
│   ├── achievements.py           # 成就配置
│   ├── catalog.py                # 物品目录
│   ├── models/                   # 数据模型
│   │   ├── user.py               # 用户
│   │   ├── couple.py             # 情侣组
│   │   ├── plan.py               # 计划/存入/心愿
│   │   ├── pet.py                # 宠物+背包
│   │   ├── extra.py              # 纪念日/礼物/待办
│   │   ├── social.py             # 等级/便签/任务/日志
│   │   ├── card.py               # 贺卡
│   │   ├── card_task.py          # 卡片任务
│   │   ├── checkin.py            # 签到
│   │   └── achievement.py        # 成就进度
│   ├── routes/                   # API 路由
│   │   ├── user.py               # 微信登录/昵称
│   │   ├── couple.py             # 绑定伴侣
│   │   ├── plan.py               # 存钱计划
│   │   ├── pet.py                # 宠物
│   │   ├── gacha.py              # 抽卡
│   │   ├── checkin.py            # 签到/火花
│   │   ├── social.py             # 经验/便签/任务
│   │   ├── extra.py              # 纪念日/礼物/待办
│   │   ├── card.py               # 贺卡
│   │   ├── card_task.py          # 卡片任务
│   │   ├── achievement.py        # 成就
│   │   └── admin.py              # 管理后台
│   ├── schemas/                  # Pydantic 请求/响应模型
│   └── services/
│       └── auth.py               # JWT + openid 认证
├── weapp/                        # 微信小程序前端
│   ├── app.js/json/wxss          # 全局配置
│   ├── utils/                    # 工具库
│   │   ├── api.js                # API 封装
│   │   ├── theme.js              # 主题管理
│   │   └── icons.js              # 图标库
│   ├── pages/                    # 各页面
│   └── images/                   # 图标资源
├── assets/pets/                  # 宠物图片资源
├── .env                          # 微信/数据库凭证（已 gitignore）
└── docs/design/                  # 设计文档
```

---

## 八、UI 设计规范

**主题：「Bloom」粉调实色**
- 主色：#D65C8A (粉红)
- 辅色：#F8A5C4 (浅粉)
- 卡片：白色 + 1px #FFD6E8 描边
- 背景：渐变粉 (#fff5fb → #ffe8f2 → #ffd6ea)
- 圆角：10px/16px/20px/999px
- 阴影：粉调透明阴影

设计原则：无毛玻璃（微信兼容）、实色块面、柔和粉调。
