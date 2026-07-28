# MechabellumData

钢铁指挥官（[Mechabellum](https://store.steampowered.com/app/669330/)）兵种数据提取与监控项目。

## 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 逆向分析 | ✅ | Il2CppDumper 完整提取类型结构、字段布局 |
| 数据采集 | ✅ | 游戏内手动采集 36 个单位 v1.11 属性表 |
| 平衡监控 | ✅ | Steam RSS 自动检测 + Claude API 解析 + 自动更新 xlsx |
| 前端展示 | ✅ | 纯静态 HTML 数据表，排序/筛选/详情 |
| 内存提取 | ⚠️ | 结构已确认，运行时定位未完成 |

## 快速开始

```bash
# 查看前端（双击打开）
frontend/index.html

# 检查平衡性更新
python balance_monitor.py --test

# 初始化监控缓存
python balance_monitor.py --init
```

## 文件结构

```
MechabellumData/
├── balance_monitor.py              # 平衡性监控主入口
├── steam_fetcher.py                # Steam RSS 抓取 + 缓存
├── change_parser.py                # Claude API 变更解析
├── sheet_updater.py                # Excel 读写更新
├── config.py                       # 配置常量
├── convert_to_json.py              # xlsx → JSON 转换
├── build_frontend.py               # 构建前端 HTML
├── frontend/
│   └── index.html                  # 兵种数据展示页（双击打开）
├── 钢铁指挥官兵种单位数据表7.29.xlsx  # 基准数据表
├── Mechabellum_Unit_Data.CT        # CE 作弊表
├── 游戏原始数据解析.md              # 逆向分析完整文档
├── 项目复盘.md                      # 全部方案记录 + 经验教训
├── 操作指南.md                      # CE 操作指南
└── 开发文档.txt                     # 对话记录
```

## 文档

| 文件 | 内容 |
|------|------|
| [游戏原始数据解析.md](./游戏原始数据解析.md) | 数据模型、单位 ID、存储位置、服务器 API |
| [项目复盘.md](./项目复盘.md) | 6 种方案尝试、核心障碍、经验教训 |
| [操作指南.md](./操作指南.md) | Cheat Engine 内存扫描操作 |
| [开发文档.txt](./开发文档.txt) | 全部 10 轮对话记录 |

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
程序集：GRCore / GRClient / GRFight / ConfigDataProtocol
```

## License

MIT
