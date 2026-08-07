# MechabellumData

钢铁指挥官（[Mechabellum](https://store.steampowered.com/app/669330/)）兵种数据监控项目。

自动监控 Steam 平衡性公告 → Deepseek 解析数值变动 → 更新数据表 → 前端即时展示。

指导老师：[**@流影**](https://space.bilibili.com/11623264?spm_id_from=333.1387.follow.user_card.click)

## 🌐 在线查看

**国内访问：** https://mechabellumdata.netlify.app/

**国际备份：** https://LuckLuffy.github.io/MechabellumData/

- 免 API Key、免安装、直接看数据
- 每周一自动更新，数据更新时网页自动热更新
- 双站同步：Netlify + GitHub Pages

## 离线查看（免 API Key）

想直接查看兵种数据，下载最新的 [`frontend/index.html`](frontend/index.html) 即可：

```
1. 下载 index.html
2. 双击用浏览器打开
3. 无需服务器、无需注册、无需联网 —— 离线查看全部 36 个单位数据
   （含攻击力/对单输出/爆发峰值/对单DPS/总DPS/性价比等列，支持排序/筛选/公式/日志选项卡）
```

> 这是纯静态数据页，数据已内嵌，展示的是构建时的数据快照；
> 在线版本（上面双站）由每周自动更新维护，数据变化时网页自动刷新。

## 从源码运行

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
| **前端展示** | 36 单位数据表（攻击力/对单输出/爆发峰值/对单DPS/总DPS/性价比等），排序/筛选/详情弹窗，公式/日志选项卡，悬停高亮 |
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
├── server.py                   # 本地 HTTP 服务器 + API
├── balance_monitor.py          # 检查管线 run_check()
├── steam_fetcher.py            # Steam RSS 抓取 + 缓存
├── change_parser.py            # Deepseek 变更解析
├── sheet_updater.py            # Excel 读写 + 版本累积
├── convert_to_json.py          # xlsx → 前端 JSON
├── build_frontend.py           # 构建前端 HTML（local/web 双模式）
├── build_web.py                # 构建网页版静态站（web/）
├── config.py                   # 配置 + .env 加载（支持冻结路径）
├── requirements.txt            # 依赖清单
├── tests/                      # 28 个 unittest
├── .github/workflows/update.yml # 每周 AI agent（自动更新+部署 Pages）
├── frontend/index.html         # 本地服务器前端（含 API 按钮）
├── web/                        # 网页版静态站（GitHub Pages + Netlify 双部署）
├── netlify.toml                # Netlify 镜像配置（发布 web/）
├── 钢铁指挥官兵种单位数据表7.29.xlsx  # 基准数据表
└── local/                      # 本地私有文档 + 已退役 exe 打包归档（不推送）
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

## 计算公式与规则

| 字段 | 公式 | 说明 |
|------|------|------|
| 攻击力 | — | 单管单发伤害 |
| 对单输出 | 攻击力 × 弹药数 | 多弹药单位：暴雨×4、鬼鳐×2、先知×2、恶灵×4、霸主×4、泰山×4、战争工厂×2 |
| 爆发峰值 | 对单输出 × 数量 | 雷霆 ×3、深渊 ×10（总共20次判定取中间值10次）|
| 对单DPS | 对单输出 ÷ 攻击间隔 | 深渊例外：爆发峰值 ÷ 间隔 |
| 总DPS | 对单DPS × 数量 | 全队持续输出 |
| 总血量 | 单体血量 × 数量 | 全队血量 |
| 输出性价比 | 总DPS ÷ 造价 | 单位造价输出效率 |
| 血量性价比 | 总血量 ÷ 造价 | 单位造价血量效率 |

> **深渊**：爆发峰值 ×10（10次判定），对单DPS 用爆发峰值÷间隔（持续输出含倍率）
> **雷霆**：爆发峰值 ×3（3道闪电分别索敌），对单DPS 用对单输出÷间隔（打单只计算一道闪电伤害）

网页前端「公式」选项卡有同样内容。

## 测试

```bash
python -m unittest discover tests   # 28 tests
```

欢迎各位指挥官提意见！

## License

**MIT**

---

⭐ **求求点个小星星，谢谢各位指挥官！** ⭐

如果这个工具帮到了你，欢迎给仓库点个 Star，支持后续持续更新。
