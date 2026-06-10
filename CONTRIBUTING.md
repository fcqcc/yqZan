# 贡献指南

> 欢迎给 auto-hub 贡献自动化项目！

---

## 如何贡献

### 1. 提 Issue

发现 bug 或有新想法？先开个 Issue 讨论。

**Issue 模板**：

#### Bug 报告

```
**问题描述**：清楚描述 bug
**复现步骤**：1. 2. 3.
**期望结果**：...
**实际结果**：...
**环境**：操作系统 / Python 版本 / ...
**截图**：（如果有）
```

#### 功能建议

```
**需求描述**：...
**使用场景**：...
**替代方案**：（如果有）
```

### 2. 提 PR

#### Fork + Clone

```bash
# 1. Fork 仓库
# 2. Clone 你的 fork
git clone https://github.com/你的用户名/auto-hub.git
cd auto-hub

# 3. 创建新分支
git checkout -b feature/your-feature-name
```

#### 新增项目结构

如果你要新增一个自动化项目，在 `modules/` 下创建：

```
modules/你的项目名/
├── app/             # 主应用代码
├── config/          # 配置文件
├── scripts/         # 辅助脚本
├── static/          # 静态资源
├── docs/            # 项目文档
├── README.md        # 项目说明（含引流）
├── openapi.json     # API 文档（如果有）
├── requirements.txt # Python 依赖
└── RAPIDAPI.md      # 第三方 API 说明（如果有）
```

#### 提交规范

```bash
git add .
git commit -m "feat: 添加 xxx 自动化项目"
git push origin feature/your-feature-name
```

**Commit 类型**：
- `feat`: 新功能
- `fix`: 修 bug
- `docs`: 文档更新
- `style`: 格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

#### 提 PR

在 GitHub 上开 Pull Request，描述：
- 你做了什么
- 为什么这么做
- 怎么测试

---

## 项目的 3 部分要求

每个自动化项目都要包含 3 部分（参考 [docs/sop/project-patterns.md](./docs/sop/project-patterns.md)）：

### 1. 完整代码（app/ + scripts/）
- 主脚本 30 行内
- 逐行中文注释
- 错误处理
- 环境变量读配置

### 2. 项目文档（docs/）
- README.md：项目说明
- API 文档（如果有）
- FAQ.md：常见问题
- 5+ 常见问题 + 处理方案

### 3. 一键生成指南（可选）
- quick-prompt/one-line.md
- 用户可以丢给 AI 自动生成简化版

---

## 代码规范

### Python 风格

- 遵循 PEP 8
- 函数命名：snake_case
- 类命名：PascalCase
- 常量：UPPER_SNAKE_CASE
- 注释用中文

### Commit 规范

参考 [Conventional Commits](https://www.conventionalcommits.org/)。

---

## 行为准则

- 尊重他人
- 接受建设性批评
- 关注对个人和集体最有利的事
- 表现出对社区成员的同理心

---

## 联系方式

- GitHub Issue：提问题
- 微信群：加 [dtw948270568] 备注"自动化"
- 公众号：「游戏好价精选」

---

## 许可证

贡献的代码将采用 [MIT License](./LICENSE)。