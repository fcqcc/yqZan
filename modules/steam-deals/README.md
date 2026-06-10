# Steam 好价推送

> 每天自动抓 Steam 折扣游戏，推送到你的微信。
> 独立模块，下载就能用，不依赖任何其他模块。

## 这是什么

每天 8:00 自动抓取 Steam 商店折扣游戏，筛选出史低 + 高折扣的好价，推送到你的微信。  
你也可以随时打开网页查看当天好价列表。

**搭建成本：¥0** | **维护时间：约 10 分钟/月** | **已稳定运行**

## 一键启动

```bash
# 1. 进模块目录
cd auto-hub/modules/steam-deals

# 2. 装依赖
pip install -r requirements.txt

# 3. 配环境（只配推送用，不配也能看网页）
cp config/.env.example .env
# 编辑 .env 填入 WECHAT_APPID 和 WECHAT_APPSECRET

# 4. 启动网页服务
uvicorn app.main:app --host 0.0.0.0 --port 5050

# 5. 浏览器打开 http://localhost:5050
```

## 配置 crontab（每天 8:00 自动抓取）

```bash
crontab -e
# 加一行：
0 8 * * * cd /path/to/auto-hub/modules/steam-deals && python scripts/fetch_daily.py >> logs/cron.log 2>&1
```

## 目录结构（下载后直接用）

```
steam-deals/
├── README.md              ← 你在看这个
├── requirements.txt       ← 装依赖
├── config/
│   └── .env.example       ← 环境变量模板
├── app/                   ← 源代码
├── scripts/               ← 每日抓取脚本
├── data/                  ← 数据库
└── static/                ← 网页
```

## 技术栈

| 组件 | 用啥 |
|------|------|
| 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite（零配置） |
| 抓取 | requests |
| 推送 | 微信公众号 |
| 部署 | 阿里云 + crontab |

## 给 Agent 的说明

```yaml
人设: 29岁程序员奶爸，辞职三年在家带娃
技术栈: Python + FastAPI + SQLite

启动方式:
  cd auto-hub/modules/steam-deals
  pip install -r requirements.txt
  uvicorn app.main:app --host 0.0.0.0 --port 5050

常见问题:
  配了 .env 但推送失败 → 检查 WECHAT_APPID / WECHAT_APPSECRET
  端口 5050 被占用 → ss -tlnp | grep 5050 → kill
  没数据 → 跑一次 python scripts/fetch_daily.py
  不想配推送也能用 → 跳过 .env，网页照样看

安全:
  .env 有 API Key → 不要提交到 Git
  data/steam_deals.db → 定期备份
```
