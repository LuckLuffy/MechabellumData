# MechabellumData

游戏文件逆向分析项目——从 [Mechabellum（钢铁指挥官）](https://store.steampowered.com/app/669330/) 中提取兵种单位数据。

## 项目状态

| 状态 | 说明 |
|------|------|
| ✅ 数据模型 | Il2CppDumper 完整提取类型结构、字段布局、字符串表 |
| ✅ 存储定位 | 确认数据在 `scuffle_assets_all.bundle` 的 CAB 容器中 |
| ⚠️ 数值提取 | 需要 AssetRipper 完整解析 CAB 或 BepInEx 运行时注入 |

## 文档

| 文件 | 内容 |
|------|------|
| [游戏原始数据解析.md](./游戏原始数据解析.md) | 数据模型定义、单位 ID 列表、存储位置、服务器 API |
| [操作指南.md](./操作指南.md) | Cheat Engine 内存扫描操作指南 |
| [项目复盘.md](./项目复盘.md) | 全部方案尝试记录、经验教训、未来方向 |

## 脚本

| 文件 | 用途 |
|------|------|
| `Mechabellum_Unit_Data.CT` | Cheat Engine 7.5 作弊表（Lua 自动扫描） |
| `extract_unit_data.py` | Python pymem 内存读取框架 |
| `scan_memory.py` | IL2CPP 堆扫描脚本 |
| `extract_with_ripper.py` | AssetRipper Web API 自动化 |

## 关键技术发现

```
游戏引擎：Unity 2022.3.62f3 + IL2CPP + Addressables v1.22.3
核心程序集：GRCore / GRClient / GRFight / ConfigDataProtocol

数据模型：
  MechData (战斗属性)     CardData (卡片数据)
  ├─ life (int)           ├─ baseMoney (int)
  ├─ damage (int)         ├─ unlockPrice (int)
  ├─ moveSpeed (int)      ├─ mechID (int)
  ├─ isFly (bool)         ├─ mechCount (int)
  ├─ mechType (enum)      ├─ slotSize (int)
  └─ moveType (enum)      └─ maintenanceSupply (int)

数据容器：
  Config.Instance → ConfigDataContainer
    ├─ mechDatas  (List<MechData>)  30+ 单位
    └─ cardDatas  (List<CardData>)  30+ 单位
```

## 工具截获

| 工具 | 用途 |
|------|------|
| [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) | IL2CPP 元数据解析 |
| [UnityPy](https://github.com/K0lb3/UnityPy) | Python 读取 Unity AssetBundle |
| [AssetRipper](https://github.com/AssetRipper/AssetRipper) | Unity 资源可视化导出 |
| [Cheat Engine](https://www.cheatengine.org/) | 运行时内存扫描 |

## License

MIT
