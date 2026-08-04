# 前后端连接与平衡性监控 — 设计文档

日期：2026-08-04
状态：已批准

## 背景

MechabellumData 项目已有：
- 后端监控脚本（`balance_monitor.py` + `steam_fetcher.py` + `change_parser.py` + `sheet_updater.py`）——能从 Steam RSS 检测平衡性公告、解析数值变动、更新 xlsx 数据表
- 纯静态前端（`frontend/index.html`）——展示 36 个单位的数据表，目前只是静态内嵌数据

需求：把前后端连接起来，实现"前端按钮触发监控 + 自动轮询 + 平衡性更新自动应用到数据表并刷新前端"。

## 关键决策（已确认）

| 决策 | 值 |
|------|-----|
| 触发方式 | 前端「检查更新」按钮 + 自动轮询（① 后端启动时 ② 每 30 天） |
| 变更解析 | Deepseek API（Anthropic 兼容端点） |
| 模型 | `deepseek-v4-flash` |
| base_url | `https://api.deepseek.com/anthropic` |
| 服务器端口 | 8800 |
| 服务器实现 | Python 标准库 `http.server`（零新依赖） |

## 架构

```
server.py  (Python 标准库 http.server, 端口 8800)
│
├── 静态:  GET /              → 前端页面
├── 状态:  GET /api/status    → { last_check, current_version, has_new }
├── 数据:  GET /api/data      → 最新单位数据 JSON
├── 记录:  GET /api/changelog → 平衡性变更历史
└── 触发:  POST /api/check    → 运行监控管线
```

## 检查管线（POST /api/check）

```
1. find_new_posts()        → 从 Steam RSS 找新公告
2. is_balance_update()     → 关键词分类
3. parse_with_deepseek()   → Deepseek 提取结构化数值变动
4. apply_change()          → 应用到最新 xlsx
5. 保存新版 xlsx → outputs/
6. 重建 frontend JSON/JS   → 前端数据同步更新
7. log_changes()           → 追加变更记录
8. 返回 { applied, summary, changes }
```

## 组件与改动

### 1. `server.py`（新建）
- `http.server.ThreadingHTTPServer` 端口 8800
- 路由表：
  - `GET /` → 返回 `frontend/index.html`
  - `GET /api/status` → 读 `cache/last_check.json` + 检测新公告（不触发解析）
  - `GET /api/data` → 返回 `frontend/unit_data.json`
  - `GET /api/changelog` → 返回 `cache/change_log.json`
  - `POST /api/check` → 运行完整监控管线，返回结果 JSON
- 静态资源：仅需 `index.html`（数据内嵌，无需其他静态文件）
- MIME 处理：`text/html`、`application/json`

### 2. `change_parser.py`（修改）
- 从 `anthropic.Anthropic` 改为使用 Deepseek 的 Anthropic 兼容端点：
  ```python
  client = anthropic.Anthropic(
      api_key=DEEPSEEK_API_KEY,
      base_url="https://api.deepseek.com/anthropic",
  )
  model = "deepseek-v4-flash"
  ```
- 读取配置：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 从 `.env` / `config.py`
- 保留离线模式：解析失败时公告存 `cache/parsed_posts/`

### 3. `config.py`（修改）
- 新增：`SERVER_PORT = 8800`
- 新增：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`
- `.env` 加载：在 `config.py` 内手写一个小助手函数（逐行解析 `KEY=VALUE`，跳过注释），**不引入 python-dotenv 新依赖**

### 4. `.env`（修改，gitignore 已排除）
- 填入 `DEEPSEEK_API_KEY=sk-0d29...`
- `DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic`
- `DEEPSEEK_MODEL=deepseek-v4-flash`

### 5. `balance_monitor.py`（重构）
- 把检查管线抽成可复用函数 `run_check() -> dict`，供 server.py 调用
- 返回结构化结果而非仅 print
- CLI 入口保留

### 6. `frontend/index.html`（修改，经 build_frontend.py 生成）
- 工具栏加「检查更新」按钮
- 加状态条：上次检查时间、当前版本、新公告数量
- `setInterval` 每 30 分钟轮询 `/api/status` 仅刷新状态显示（不触发检查）；检查本身由后端启动时 + 每 30 天定时器 + 前端按钮触发
- 数据源：优先 `fetch('/api/data')`（服务器模式）；请求失败时**降级回内嵌数据**（保留离线双击可用性）
- 变更记录页：优先 `/api/changelog`，失败时静默隐藏该标签

### 7. `build_frontend.py`（保持）
- 检查后重建 `frontend/unit_data.json` + `index.html` 数据
- server.py 检查管线第 6 步调用

## 数据流

### 手动检查（按钮）
```
点击「检查更新」
  → POST /api/check
  → 管线执行（检测→解析→应用→重建）
  → 返回 { applied, summary }
  → 前端刷新数据 + 变更记录
```

### 自动轮询
```
① 后端启动时
  → 自动执行一次 POST /api/check

② 每 30 天（未来扩展，当前阶段不实现）
  → 预留定时器接口，架构上可平滑接入
  → 当前阶段仅实现：后端启动检查 + 前端手动按钮
```

## 错误处理

| 场景 | 处理 |
|------|------|
| 无新公告 | 返回 "无新公告"，`applied=0` |
| Deepseek 调用失败 | 公告存 `cache/parsed_posts/`，返回部分成功 + 错误信息 |
| Steam 网络失败 | 返回错误信息，前端显示提示，不影响现有数据 |
| 端口占用 | 启动时报错，提示换端口 |

## 验证方式

1. `python server.py` 启动，浏览器开 `http://localhost:8800`
2. `curl http://localhost:8800/api/status` — 返回状态 JSON
3. `curl http://localhost:8800/api/data` — 返回 36 单位数据
4. `curl -X POST http://localhost:8800/api/check` — 执行检查，无新公告时应返回 applied=0
5. 模拟：手动往 cache 加一条新公告 → 再 check → 验证解析和应用链路
6. 前端点击按钮 → 数据刷新 + 变更记录更新

## 非目标（YAGNI）

- 不做多用户/认证（本地单人工具）
- 不做数据库持久化（沿用 xlsx + JSON 文件）
- 不做部署到公网（纯本地）
- 不做前端历史版本对比图（暂只显示当前数据 + 变更记录文本）
- 不做 30 天定时轮询（当前阶段；预留接口，未来扩展）
