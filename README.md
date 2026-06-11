# auto-hub — 小赫的自动化项目集合

<div align="center">

**🤖 AI 时代新程序员 · 自动化一键搭建聚合平台**

> 每周 1 套自动化项目。
> 复制一句话给 AI，AI 引导你一步步搭建。

[![GitHub stars](https://img.shields.io/github/stars/fcqcc/auto-hub?style=social)](https://github.com/fcqcc/auto-hub)
[![GitHub forks](https://img.shields.io/github/forks/fcqcc/auto-hub?style=social)](https://github.com/fcqcc/auto-hub)
[![License](https://img.shields.io/github/license/fcqcc/auto-hub)](https://github.com/fcqcc/auto-hub/blob/main/LICENSE)

[🌟 GitHub Star](https://github.com/fcqcc/auto-hub) · [🍴 Fork](https://github.com/fcqcc/auto-hub/fork) · [🏠 Gitee](https://gitee.com/YuDaBaiJia/auto-hub) · [📖 Docs](./docs/architecture.md)

</div>

---

## 👋 我是谁

程序员奶爸，辞职在家带娃，利用AI搓自动化项目。

每周分享 1 套「AI 一键自动化」项目，从零到跑通只需要将对应项目的文档丢给智能体，一键复现自动化项目。

| 平台 | 账号 | 说明 |
|---|---|---|
| **微信公众号** | 游戏好价精选 | 每周 1 套新自动化 + AI 教程 |

> 📱 **扫码关注公众号，每周 1 套新自动化**：
>
> ![公众号二维码](./docs/qrcode.jpg)

---

## 🚀 项目如何使用

### 4 种用法（按人群选）

#### 用法 1：直接 clone 整个项目（懂技术的人）

```bash
# 1. 克隆整个仓库
git clone https://github.com/fcqcc/auto-hub.git
cd auto-hub

# 2. 在 modules/ 文件夹中找到你感兴趣的项目
ls modules/

# 3. 看完整代码
cat modules/steam-deals/app/main.py

# 4. 一键跑通
cd modules/steam-deals
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python app/main.py
```

#### 用法 2：稀疏克隆（只下你想要的模块）

```bash
# 1. 初始化空仓库
mkdir auto-hub && cd auto-hub
git init
git remote add origin https://github.com/fcqcc/auto-hub.git

# 2. 启用 sparse-checkout
git config core.sparseCheckout true
echo "modules/steam-deals/*" > .git/info/sparse-checkout

# 3. 拉取指定模块
git pull origin master

# 4. 看 README 跑通
cd modules/steam-deals
cat README.md
```

#### 用法 3：按 README.md 文档配置（半懂不懂的人）

不用懂代码，跟着文档走：

1. 进入 `modules/steam-deals/` 目录
2. 打开 `README.md` 看说明
3. 跟着 `docs/` 下的步骤一步步操作
4. 遇到问题看 `FAQ.md`

#### 用法 4：丢给 AI 一键生成（完全不懂的人）

不用懂任何东西：

1. 进入 `modules/steam-deals/quick-prompt/`
2. 复制 `one-line.md` 里的启动语
3. 粘贴给任意 AI（Claude / GPT-4 / DeepSeek）
4. AI 引导你回答 2 个问题
5. AI 自动生成完整项目包

---

## 📦 项目列表

| # | 项目名 | 任务类型 | 状态 |
|---|---|---|---|
| 01 | [Steam 折扣推荐](./modules/steam-deals/) | API 调用型 | ✅ 已完成 |
| 02 | Steam 好价推送 | RSS 抓取型 | ✅ 已完成 |
| 03 | GitHub Trending 推送 | API 调用型 | ⏳ 计划中 |
| 04 | 豆瓣 Top250 监控 | 爬虫型 | ⏳ 计划中 |
| 05 | 每日邮件汇总 | 邮件型 | ⏳ 计划中 |
| 06 | Notion 自动备份 | API 调用型 | ⏳ 计划中 |
| 07 | 微信群垃圾过滤 | API 调用型 | ⏳ 计划中 |
| 08 | B 站收藏更新 | API 调用型 | ⏳ 计划中 |
| 09 | 即刻 Tab 推送 | API 调用型 | ⏳ 计划中 |
| 10 | 微博热搜推送 | 爬虫型 | ⏳ 计划中 |
| 11 | RSS 聚合 | RSS 抓取型 | ⏳ 计划中 |
| 12 | 邮件聚合 | 邮件型 | ⏳ 计划中 |

**每周 1 个新项目**——**3 个月 12 个**——**关注公众号第一时间收到推送**。

---

## 📂 仓库结构

```
auto-hub/
├── README.md              # 你正在看
├── AGENTS.md              # 给 agent 的总指令
├── CONTRIBUTING.md        # 贡献指南
├── LICENSE                # MIT 许可证
│
├── docs/                  # 总文档
│   ├── architecture.md    # 整体架构说明
│   ├── how-to-use.md      # 使用说明
│   ├── agent-workflow.md  # 怎么和 agent 协作
│   ├── sop/               # SOP 文档
│   │   ├── v4-flow.md
│   │   ├── project-patterns.md
│   │   └── agent-training.md
│   ├── qrcode.jpg         # 公众号二维码
│   └── wechat-qrcode.jpg  # 微信二维码
│
└── modules/               # 所有自动化项目
    ├── steam-deals/
    │   ├── app/           # 主应用
    │   ├── config/        # 配置
    │   ├── scripts/       # 脚本
    │   ├── static/        # 静态资源
    │   ├── docs/          # 项目文档
    │   ├── README.md      # 项目说明
    │   ├── openapi.json   # API 文档
    │   ├── requirements.txt
    │   └── RAPIDAPI.md
    └── ... 更多模块
```

---

## 🤝 贡献

欢迎提 issue 和 PR！

如果你也想分享自己的自动化项目，看 [CONTRIBUTING.md](./CONTRIBUTING.md)。

---

## 📜 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 💬 交流群

扫码加我微信（备注"自动化"），拉你进群：

![微信二维码](./docs/wechat-qrcode.jpg)

群里有 100+ 程序员奶爸/奶妈，一起交流自动化心得。

---

<div align="center">

**👇 关注公众号，每周 1 套新自动化 👇**

![公众号二维码](./docs/qrcode.jpg)
</div>