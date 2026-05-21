# 卡片任务系统 — 实现方案

> 使用卡片后，对方主页出现任务，交互双方确认/反馈流程

## 设计方案

### 核心模型

新建 `CardTask` 表，记录每个卡片任务的生命周期：

```
字段          说明
─────────────────────────────────────────
id            主键
couple_id     所属情侣
card_item_id  卡片物品ID（chore_dishes 等）
title         展示名称（"洗碗🧹" 等）
assigner_id   发起者
assignee_id   接收方
status        状态流转
created_at    创建时间
updated_at    更新时间
```

### 状态流转

```
                      ┌─ 完成 ─→ completed_pending ── 确认完成 ─→ completed
                      │                           └─ 未完成 ─→ pending（退回）
pending ──→ 接收方响应 ─┤
                      └─ 我不要卡 ─→ declined
```

### 锁定规则

同一 `couple_id + card_item_id` 的 `pending / completed_pending` 状态存在时，禁止再次发起同类卡片。

---

### 后端改动

| 文件 | 改动 |
|------|------|
| `app/models/card_task.py` | 新建 CardTask 模型 |
| `app/models/__init__.py` | 注册新模型 |
| `app/routes/card_task.py` | 新建路由：use / list / complete / decline / confirm / dispute |
| `app/routes/pet.py` | 修改 `useItem`：卡牌类跳过旧逻辑 |
| `app/main.py` | 注册 card_task_router |

### 前端改动

| 文件 | 改动 |
|------|------|
| `utils/api.js` | 新增 card-task API 函数 |
| `pages/backpack/backpack.js` | 卡牌类物品走新流程（不走 useItem） |
| `pages/home/home.js` | 加载卡片任务数据 + 处理交互 |
| `pages/home/home.wxml` | 展示卡片任务区域 |
| `pages/home/home.wxss` | 卡片任务样式 |

---

### API 设计

```
POST /api/card-tasks/use          → 使用卡片、创建任务
GET  /api/card-tasks/active       → 获取当前活跃卡片任务（双方各自所需）
POST /api/card-tasks/{id}/complete        → 接收方：已完成
POST /api/card-tasks/{id}/decline         → 接收方：我不要卡
POST /api/card-tasks/{id}/confirm         → 发起方：确认完成
POST /api/card-tasks/{id}/dispute         → 发起方：未完成（退回）
```

### 前端展示逻辑

**发起方首页：**
- 有 `assignerPending` 任务 → 显示 "卡片生效中，等待(对方)确认"
- 有 `completedPending` 任务 → 显示 "对方声称已完成，是否确认？" + [确认完成] [未完成]

**接收方首页：**
- 有 `pending` 任务 → 显示任务卡片 + [已完成] [我不要卡]

---

需要我实现吗？
