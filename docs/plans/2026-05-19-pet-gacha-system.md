# 桌宠 & 抽奖系统 实现计划

> **目标：** 在"一起攒"小程序中加入桌宠系统（🐷默认宠物 + 🦊🐱🐉等抽卡获得），支持成长、亲密度、分支进化、抽奖单抽/十连、背包图鉴。

**架构思路：**
- 后端新增 `pets` / `gacha_items` / `inventory` 三张表
- 宠物数据模型包含 type / form / intimacy / unlocked_forms 字段
- 抽奖用纯概率表 + 券消耗，不做额外货币
- 前端宠物用 CSS 动画做走动/状态切换，不引入游戏引擎

**依赖：** 需新建 `app/models/pet.py`、`app/routes/pet.py`、`app/routes/gacha.py`

---

## Phase 1: 后端数据模型

### Task 1: 创建宠物数据模型

**Objective:** 定义 Pet、GachaItem、Inventory 三个数据表

**Files:**
- Create: `app/models/pet.py`

**Pet 表设计：**

```python
class Pet(Base):
    __tablename__ = "pets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    pet_type = Column(String(16), nullable=False)  # pig / fox / cat / unicorn / dragon
    nickname = Column(String(32), default="")
    intimacy = Column(Integer, default=0)  # 0-100
    is_active = Column(Boolean, default=False)  # 当前展示的
    unlocked_forms = Column(Text, default=json.dumps(["baby"]))  # JSON array of form names
    current_form = Column(String(16), default="baby")
    created_at = Column(DateTime, default=datetime.now)
```

**用户抽奖物品（记录谁抽到了什么，但不存细节属性）：**

其实不需要 GachaItem 表——Inventory 就够。用户抽到的东西直接存进 Inventory。

**Inventory 表设计：**

```python
class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_id = Column(Integer, ForeignKey("couples.id"), nullable=False, index=True)
    item_type = Column(String(16), nullable=False)  # pet / accessory / background / evolution_item / consumable
    item_id = Column(String(32), nullable=False)  # e.g. "fox", "bow", "crown", "gold_ingot"
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
```

**DrawTicket（抽奖券数量，存 couple 级别）：**
在 Couple 表加一个字段 `draw_tickets`，或者单独一张表。简单点直接 Couple 表加字段。

Actually, simplest: couple 表加个 `draw_tickets = Column(Integer, default=0)` 字段。

**Verify:**
```bash
cd /home/root_1/workspace/couple-promise-v2
python3 -c "from app.models.pet import Pet, Inventory; print('models loaded')"
```

---

### Task 2: 初始化默认宠物

**Objective:** 注册/首次登录时，自动给用户分配一只默认 🐷 小粉猪

**Files:**
- Modify: `app/routes/user.py`（注册处）+ `app/routes/pet.py`（init函数）

注册时（已有个人 couple 创建后）：
```python
pet = Pet(couple_id=user.couple_id, pet_type="pig", intimacy=0, is_active=True, unlocked_forms=json.dumps(["baby"]), current_form="baby")
db.add(pet)
```

同时写一个独立的 init 函数给已有用户补初始宠物。

---

### Task 3: 创建宠物 API

**Objective:** CRUD 宠物管理、形态切换、亲密度操作

**Files:**
- Create: `app/routes/pet.py`

**Endpoints:**

| Method | Path | 功能 |
|--------|------|------|
| GET | `/api/pets` | 获取用户所有宠物 |
| POST | `/api/pets/active` | 切换当前活跃宠物 `{pet_id}` |
| POST | `/api/pets/{id}/form` | 切换宠物形态 `{form}` |
| POST | `/api/pets/{id}/feed` | 喂食（增加亲密+互动判定） |
| POST | `/api/pets/evolve` | 使用进化道具 `{pet_id, item_id}` |
| GET | `/api/pets/unlockable-forms` | 返回当前可解锁但未解锁的形态 |

**核心逻辑（形态解锁）：**

```python
def get_unlocked_forms(total_saved: float):
    """根据总存款返回已解锁形态列表"""
    forms = ["baby"]
    if total_saved >= 1000: forms.append("teen")
    if total_saved >= 5000: forms.append("adult")
    if total_saved >= 20000: forms.append("deluxe")
    if total_saved >= 100000: forms.append("legend")
    return forms
```

每次 API 调用时重新计算：检查 `unlocked_forms` 是否少于当前应解锁的，少则补上。

**Check endpoint (用于首页状态):**

| Method | Path | 功能 |
|--------|------|------|
| GET | `/api/pets/active` | 获取当前活跃宠物完整状态（形态/亲密/动画状态） |

返回：
```json
{
  "pet_type": "pig",
  "current_form": "adult",
  "form_name": "金猪",
  "intimacy": 75,
  "intimacy_level": "happy",
  "mood": "normal",
  "unlocked_forms": ["baby","teen","adult"],
  "accessories": ["bow"]
}
```

**Verify:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/pets/active
```

---

### Task 4: 创建抽奖 API

**Objective:** 单抽、十连、概率表、券消耗

**Files:**
- Create: `app/routes/gacha.py`
- Modify: `app/models/couple.py`（加 draw_tickets 字段）

**概率表（后端写死）：**

```python
GACHA_POOL = [
    # (item_type, item_id, name, rarity, weight)
    ("consumable", "fortune_cookie", "幸运饼干🍪", "N", 18),
    ("consumable", "switch_card", "切换卡🔄", "N", 14),
    ("consumable", "intimacy_candy", "亲密糖果🍬", "N", 12),
    ("pet", "fox", "小狐狸🦊", "R", 10),
    ("accessory", "bow", "蝴蝶结🎀", "N", 8),
    ("accessory", "sunglasses", "墨镜🕶️", "R", 6),
    ("pet", "cat", "招财猫🐱", "SR", 4),
    ("consumable", "streak_protect", "免断卡🛡️", "R", 4),
    ("evolution_item", "gold_ingot", "金元宝🪙", "SR", 3),
    ("evolution_item", "love_arrow", "爱心箭🏹", "SR", 3),
    ("evolution_item", "moon_stone", "月光石🌙", "SR", 3),
    ("evolution_item", "fortune_bell", "招财铃🎴", "SR", 3),
    ("accessory", "crown", "皇冠👑", "SR", 3),
    ("background", "sakura", "樱花背景🌸", "R", 3),
    ("consumable", "reminder_horn", "提醒喇叭📣", "N", 2),
    ("background", "starry", "星光背景🌟", "SR", 2),
    ("evolution_item", "mech_core", "机械核心⚙️", "SSR", 1.5),
    ("evolution_item", "stardust", "星尘🌌", "SSR", 1.5),
    ("pet", "unicorn", "独角兽🦄", "SSR", 0.8),
    ("pet", "dragon", "金元宝龙🐉", "SSR+", 0.2),
]
```

**Endpoints:**

| Method | Path | 功能 |
|--------|------|------|
| GET | `/api/gacha/tickets` | 获取抽奖券数量 |
| POST | `/api/gacha/draw` | 单抽 `{}` → 返回抽到的物品 |
| POST | `/api/gacha/draw10` | 十连 `{}` → 返回10个物品 + 返还1张券 |

**抽奖逻辑：**

```python
def draw_once():
    total_weight = sum(item.weight for item in GACHA_POOL)
    r = random.randint(1, total_weight)
    cumulative = 0
    for item in GACHA_POOL:
        cumulative += item.weight
        if r <= cumulative:
            return item
```

**Verify:**
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/gacha/draw
```

---

### Task 5: 抽奖券获取逻辑

**Objective:** 存钱、打卡、绑定、达标时自动发放抽奖券

**Files:**
- Modify: `app/routes/plan.py`（存钱时发券）
- Modify: `app/routes/social.py`（打卡时发券）
- Modify: `app/routes/couple.py`（绑定时发券）

**辅助函数（写在 gacha.py）：**

```python
def add_draw_tickets(db: Session, couple_id: int, amount: int):
    couple = db.query(Couple).filter(Couple.id == couple_id).first()
    if couple:
        couple.draw_tickets = (couple.draw_tickets or 0) + amount
        db.commit()
```

**发放规则：**
- 存钱：每存一笔+1（日限3次）→ plan.py deliver 处加
- 首次绑定伴侣：+5 → couple.py bind 处加
- 打卡7/14/21/30天：各+3 → social.py 检查完成时加
- 目标达成：+10 → plan.py 完成时加
- 双人同日打卡：+1 → social.py 加

---

### Task 6: 背包 & 图鉴 API

**Objective:** 查看物品、使用消耗品

**Files:**
- Modify: `app/routes/pet.py` 或新建 `app/routes/inventory.py`

**Endpoints:**

| Method | Path | 功能 |
|--------|------|------|
| GET | `/api/inventory` | 获取所有物品（按类型分组） |
| POST | `/api/inventory/use` | 使用消耗品 `{inventory_id}` |
| GET | `/api/inventory/bestiary` | 图鉴：所有可获得的宠物/形态/配饰+当前解锁状态 |

**Verify:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/inventory
```

---

## Phase 2: 前端实现

### Task 7: 首页桌宠展示

**Objective:** 在首页添加 🐷 宠物走动动画 + 状态切换

**Files:**
- Modify: `weapp/pages/home/home.wxml`（宠物容器）
- Modify: `weapp/pages/home/home.wxss`（CSS动画）
- Modify: `weapp/pages/home/home.js`（加载宠物数据）

**动画设计：**
- 宠物在首页底部左右走动（translateX 循环）
- 普通状态：匀速走动
- 开心状态（刚存完钱）：原地蹦跳 + 冒出爱心粒子
- 低落状态（3天没活动）：趴下 + 呼吸动画

**纯 CSS 实现（不用 Canvas）：**

```css
.pet-walk {
  animation: petWalk 8s ease-in-out infinite alternate;
}
@keyframes petWalk {
  0% { transform: translateX(0); }
  100% { transform: translateX(200rpx); }
}
.pet-jump {
  animation: petJump 0.6s ease-out;
}
@keyframes petJump {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-40rpx); }
}
```

**表情（纯文字/emoji 代替图片）：**
```html
<view class="pet-emoji">{{petEmoji}}</view>
```

每次 API `GET /api/pets/active` 返回 `mood`：
- normal → 🐷
- happy → 🐷💕
- sad → 😴🐷

---

### Task 8: 抽奖页面（刮刮乐）

**Objective:** 抽奖入口 + 刮卡动画 + 结果展示

**Files:**
- Create: `weapp/pages/gacha/gacha.wxml`
- Create: `weapp/pages/gacha/gacha.wxss`
- Create: `weapp/pages/gacha/gacha.js`

**交互流程：**
```
首页右下角浮动按钮 🎰
  ↓
进入抽奖页
  ├── 显示当前抽奖券数量
  ├── 单抽按钮 / 十连按钮
  ├── 扭蛋机动画（CSS旋转+下落）
  └── 结果 → 刮开特效 → 展示获得的物品
```

**刮开效果：** 用 CSS mask 或覆盖层 touch move 刮开。简单版直接弹窗显示结果，不做物理刮卡。

**Verify:** 点击抽奖 → 券减少 → 弹出获得的物品

---

### Task 9: 抽奖结果展示

**Objective:** 根据稀有度展示不同动画效果

**Files:**
- Modify: `weapp/pages/gacha/gacha.js`

**动画级别：**
- N（饼干/切换卡/糖果）：淡入弹窗，显示物品
- R（狐狸/墨镜/樱花）：缩放动画 + 轻微闪光
- SR（猫/皇冠/进化道具）：金色闪光 + 放大的弹窗
- SSR（机械核心/星尘/独角兽）：全屏闪烁 + 震动
- SSR+（龙）：全屏粒子效果 + 慢动作展示

**Verify:** 多次抽奖 → 不同稀有度展示不同效果

---

### Task 10: 宠物详情/管理页面

**Objective:** 查看宠物、切换宠物、切换形态、使用道具

**Files:**
- Create: `weapp/pages/pets/pets.wxml`
- Create: `weapp/pages/pets/pets.wxss`
- Create: `weapp/pages/pets/pets.js`

**页面布局：**
```
┌─────────────────────┐
│  我的宠物            │
│                     │
│  [大号宠物展示]      │ ← 当前活跃宠物，点击互动
│  🐷 小粉猪          │
│  亲密度 ██████░░░ 75 │
│                     │
│  形态切换            │
│  baby│teen│adult│... │ ← 横向滑动，已解锁的高亮
│                     │
│  我的宠物列表         │
│  🐷 小粉猪（当前）    │
│  🦊 小狐狸           │ ← 点"设为当前"
│  🐱 招财猫           │
│                     │
│  配饰                │
│  🎀 蝴蝶结 👑 皇冠    │ ← 点击穿戴
└─────────────────────┘
```

---

### Task 11: 背包 & 图鉴页面

**Objective:** 查看所有物品、使用消耗品、查看图鉴

**Files:**
- Create: `weapp/pages/backpack/backpack.wxml`
- Create: `weapp/pages/backpack/backpack.wxss`
- Create: `weapp/pages/backpack/backpack.js`

**TAB 切换：**
```
┌─────────────────────┐
│  背包  |  图鉴       │
├─────────────────────┤
│  [背包列表]          │
│  消耗品              │
│  ├ 🍬 亲密糖果 ×3    │
│  ├ 🛡️ 免断卡 ×1     │
│  进化道具            │
│  ├ 🪙 金元宝 ×1      │
│  配饰                │
│  ├ 🎀 蝴蝶结 ×2      │
└─────────────────────┘
```

**图鉴页（全收集列表）：**

```
│  宠物              │
│  🐷 小粉猪 ✓      │
│  🦊 小狐狸 ✓      │
│  🐱 招财猫         │ ← 灰色（未获得）
│  🦄 独角兽         │
│  🐉 金元宝龙       │
│                    │
│  进化形态           │
│  🐷→金元宝猪 ✓     │
│  🐷→招财进宝 ✓     │
│  🐷→赛博猪         │
```

---

## Phase 3: 集成 & 联调

### Task 12: 首页入口 + 礼物功能

**Objective:** 首页添加桌宠区 + 抽奖入口

**Files:**
- Modify: `weapp/pages/home/home.wxml`（桌宠底座）
- Modify: `weapp/pages/home/home.wxss`
- Modify: `weapp/pages/home/home.js`（加载活跃宠物数据）

**首页布局变更：**
- 宠物放在底部（所有内容上面 float）
- 右上角加抽奖入口浮动按钮
- 存钱后宠物自动跳起开心

### Task 13: 验证全链路

**Objective:** 从注册到抽奖到桌宠到进化的全流程

**测试路径：**
1. 注册新账号 → 得到 🐷 小粉猪
2. 存一笔钱 → 获得抽奖券
3. 抽奖 → 获得道具/新宠物
4. 切换到新宠物
5. 继续存钱 → 宠物成长 → 解锁新形态
6. 使用进化道具 → 解锁分支形态
7. 连续存钱 → 亲密度上升
8. 3天不存 → 宠物低落
9. 攒抽奖券 → 十连 → 返券

---

## 目录变更总结

```
新增：
  app/models/pet.py           ← Pet, Inventory 数据模型
  app/routes/pet.py            ← 宠物 CRUD / 亲密 / 进化
  app/routes/gacha.py          ← 抽奖 / 券管理 / 概率表
  weapp/pages/gacha/           ← 抽奖页面（刮刮乐）
  weapp/pages/pets/            ← 宠物管理页面
  weapp/pages/backpack/        ← 背包 + 图鉴

修改：
  app/models/couple.py         ← +draw_tickets 字段
  app/routes/user.py           ← 注册时 init 默认宠物
  app/routes/plan.py           ← 存钱时发抽奖券
  app/routes/couple.py         ← 绑定时发券
  app/routes/extra.py          ← 打卡达标发券
  app/routes/__init__.py       ← 注册新 router
  app/main.py                  ← include 新 router
  weapp/pages/home/home.*      ← 添加宠物 + 抽奖入口
  weapp/utils/api.js           ← 新 API 封装
  weapp/app.json               ← 注册新页面
```

---

## 备注

- 所有宠物用 emoji + CSS 动画实现，不用图片资源
- 抽奖券存在 couple 表，不做单独的表
- 概率表后端写死，不改数据库（前端不暴露概率，防篡改）
- 亲密度纯前端判断（后端只存数值，mood/level 前端算）
