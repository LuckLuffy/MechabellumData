# MechabellumData

钢铁指挥官（[Mechabellum](https://store.steampowered.com/app/669330/)）兵种数据监控项目。

自动监控 Steam 平衡性公告 → Deepseek 解析数值变动 → 更新数据表 → 前端即时展示。

指导老师：[**@流影**](https://space.bilibili.com/11623264?spm_id_from=333.1387.follow.user_card.click)

## 下载使用（免命令行）

**`dist/MechaMv1.0.1.exe`**（Windows x64，单文件，约 30MB）

```
1. 下载 MechaMv1.0.1.exe
2. 双击运行 —— 弹出配置窗口，填入你的 Deepseek API Key
     （申请：https://platform.deepseek.com）
3. 点「保存」→ 自动打开浏览器 http://localhost:8800
4. 点网页「检查更新」即可自动解析平衡性公告
```

> 程序不内置任何 API Key —— 你的 Key 只存在你自己电脑的 `.env` 里，不公开。
> 首次运行（或 Key 缺失时）自动弹窗填写；点「跳过」可暂不配置，仅检测公告并保存到 `cache/parsed_posts/`，下次启动仍会提示。

重新打包：`python build_exe.py`（需先 `pip install pyinstaller`）。

### 不想注册 AI？直接下载前端页面

如果只是想查看兵种数据、不想申请 Deepseek API Key，直接下载最新的
[`frontend/index.html`](frontend/index.html) 即可：

```
1. 下载 index.html
2. 双击用浏览器打开
3. 无需服务器、无需注册、无需联网 —— 离线查看全部 36 个单位数据
   （含 DPS、爆发峰值、性价比等列，支持排序/筛选/详情）
```

> 这是纯静态数据页，数据已内嵌。区别是：静态页只能看当前数据，
> exe + AI 才能自动监控 Steam 公告并实时更新数据表。

## 从源码运行（开发）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动本地服务器（含后端启动自动检查 + 前端页面）
python server.py

# 浏览器打开
# http://localhost:8800
```

## 功能

| 功能 | 说明 |
|------|------|
| **平衡性监控** | 轮询 [Steam RSS](https://store.steampowered.com/news/app/669330/) 检测新公告 |
| **自动识别** | 关键词分类 + Deepseek（Anthropic 兼容端点）提取数值变动 |
| **自动更新** | 变动应用到 xlsx 数据表 → 重建前端数据 → 记录变更日志 |
| **触发方式** | 后端启动自动检查 + 前端「检查更新」按钮 |
| **前端展示** | 36 单位数据表，排序/筛选/详情弹窗，变更状态条 |
| **离线降级** | 无服务器时前端回退内嵌数据，双击 `frontend/index.html` 仍可用 |

## 架构

```
Steam RSS ──► steam_fetcher ──► balance_monitor.run_check()
                                        │
                                        ▼
                              change_parser (Deepseek)
                                        │
                                        ▼
                              sheet_updater (xlsx 版本化累积)
                                        │
                                        ▼
                              convert_to_json ──► frontend/unit_data.json
                                        │
                                        ▼
server.py (端口 8800) ──► 前端「检查更新」按钮 + 30min 状态轮询
```

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/status` | GET | 上次检查、当前版本、有无新公告 |
| `/api/data` | GET | 最新单位数据 JSON |
| `/api/changelog` | GET | 平衡性变更历史 |
| `/api/check` | POST | 触发一次完整检查（检测→解析→应用→重建） |

## 配置

`.env`（gitignored，不入库）：

```
DEEPSEEK_API_KEY=sk-...            # Deepseek API 密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
DEEPSEEK_MODEL=deepseek-v4-flash
SERVER_PORT=8800                   # 可选，默认 8800
```

## 文件结构

```
MechabellumData/
├── dist/MechaMv1.0.1.exe      # Windows x64 免安装版（供下载）
├── app.py                      # exe 入口（资源引导 + 启动 + 开浏览器）
├── build_exe.py                # PyInstaller 打包脚本（不嵌 key）
├── server.py                   # 本地 HTTP 服务器 + API
├── balance_monitor.py          # 检查管线 run_check()
├── steam_fetcher.py            # Steam RSS 抓取 + 缓存
├── change_parser.py            # Deepseek 变更解析
├── sheet_updater.py            # Excel 读写 + 版本累积
├── convert_to_json.py          # xlsx → 前端 JSON
├── build_frontend.py           # 构建前端 HTML
├── config.py                   # 配置 + .env 加载（支持冻结路径）
├── requirements.txt            # 依赖清单
├── tests/                      # 26 个 unittest
├── frontend/index.html         # 前端页面
├── 钢铁指挥官兵种单位数据表7.29.xlsx  # 基准数据表
└── local/                      # 本地私有文档（开发文档/操作指南/解析/复盘，不推送）
```

## 数据模型

```
MechData (战斗属性)          CardData (卡片数据)
├─ life (int)     ← HP      ├─ baseMoney (int)      ← 费用
├─ damage (int)   ← ATK     ├─ unlockPrice (int)    ← 解锁费
├─ moveSpeed (int)← 速度    ├─ mechID (int)         ← 单位ID
├─ isFly (bool)             ├─ mechCount (int)      ← 每队数量
├─ mechType (enum)          ├─ slotSize (int)       ← 部署槽
└─ moveType (enum)          └─ maintenanceSupply    ← 维护费

引擎：Unity 2022.3 + IL2CPP + Addressables v1.22.3
解析：Deepseek (Anthropic 兼容端点) · deepseek-v4-flash
```

## 测试

```bash
python -m unittest discover tests   # 26 tests
```

## License

**MIT**

---

⭐ **求求点个小星星，谢谢各位指挥官！** ⭐

如果这个工具帮到了你，欢迎给仓库点个 Star，支持后续持续更新（新版本、新兵种、平衡性自动同步）。