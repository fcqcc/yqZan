# auto-hub — 小赫的自动化项目集合

> 每个自动化项目就是一个独立模块，选一个下载就能用。
> 相互不依赖，不冲突。

## 快速使用

```bash
# 1. 浏览所有模块
ls modules/

# 2. 选一个模块，进去看说明
cat modules/steam-deals/README.md

# 3. 按说明启动即可
```

## 模块列表

| 模块 | 一句话描述 | 难度 | 依赖 | 状态 |
|------|-----------|------|------|------|
| [steam-deals](modules/steam-deals/) | Steam 好价自动追踪 + 微信推送 | ⭐ 入门 | Python + FastAPI | ✅ 稳定 |
| *(等你来加)* | | | | |

## 模块规范

每个模块都是**完整独立的**，可以直接复制到任何机器运行：

```
modules/＜模块名＞/
├── README.md              # 启动教程（人类版 + Agent 版）
├── requirements.txt       # 独立依赖清单
├── config/
│   ├── .env.example       # 环境变量模板
│   └── config.yaml        # 配置
├── src/                   # 源代码
├── scripts/               # 工具脚本
└── data/                  # 数据（可选）
```

## 给 Agent 的说明

```yaml
角色: 项目维护者
职责:
  - 帮用户浏览模块列表
  - 按需下载/启动指定模块
  - 记录踩坑经验到模块的 README

启动新模块:
  1. cd modules/<name>
  2. pip install -r requirements.txt
  3. cp config/.env.example .env（提醒用户填 Key）
  4. 按照 README 启动

排错:
  - .env 没配 → 复制模板并提示
  - 缺依赖 → pip install -r requirements.txt
  - 端口被占 → 改 config.yaml 的 port
```
