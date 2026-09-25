"""将 Excel 数据表转换为 JSON 供前端使用"""
import json
import os
from config import ROOT_DIR
from sheet_updater import load_workbook

OUTPUT_PATH = os.path.join(ROOT_DIR, "frontend", "unit_data.json")

# 飞行单位（显式清单）。
# 旧实现用「对空 > 0.5 且 移速 > 8 → 飞行」推断，对快速对空单位会误判成飞行：
# 野马、先知、台风、百夫长 都是反例（能对空但不飞），前三个当时靠 GROUND_FORCE
# 逐个打补丁，补到第四个说明规则不成立 —— 改成显式清单，对空能力不再影响飞行与否。
FLYING_UNITS = {"深渊", "霸主", "雷霆", "恶灵", "凤凰", "鬼鳐", "兵峰"}

# 对空能力（0 无 / 0.5 部分 / 1 有）。
# 2026-09 表把「对空」列下线了，但前端要用它算「飞行/地面」并显示对空值，
# 这里沿用上一版（v1.11.1.1a）发布值，保证页面与旧版一致。
# ⚠ 对空能力若发生平衡性变动，代码不会感知——需要把「对空」列加回表里。
# 百夫长为 2.0 新单位，对空值由用户确认（可对空 = 1）。
ANTI_AIR = {
    "弧光": 0.5, "长弓": 1, "魔眼": 0.5, "尖牙": 1, "狼蛛": 0.5, "鬼鳐": 1,
    "凤凰": 1, "兵峰": 1, "野马": 1, "先知": 1, "恶灵": 1, "台风": 1,
    "沙虫": 0.5, "熔点": 1, "雷霆": 1, "霸主": 1, "深渊": 1, "泰山": 0.5,
    "丧钟": 1, "百夫长": 1,
}
ANTI_AIR_DEFAULT = 0

# ===== 公式规则（2026-09 表结构，用户设计）=====
# 表内只存原始列「攻击力 + 弹药量」，对单输出/爆发峰值/对单DPS 全部由本模块推算。
# 弹药量已是表内一列，不再需要按单位名硬编码弹药数。
#
# 唯一保留的特殊倍率：雷霆一次攻击放 3 道闪电、各打各的目标 ——
# 打单个目标只吃得到一道（所以对单输出不含 ×3），但全队齐射上限要算满 3 道，
# 因此只有爆发峰值吃这个倍率。深渊的 ×10 已折进表内「弹药量」列，不走这里。
BURST_MULTIPLIER = {"雷霆": 3}


def compute_derived(name, atk, ammo, count, interval) -> tuple:
    """推算 对单输出/爆发峰值/对单DPS。

    规则：
      对单输出 = 攻击力 × 弹药量
      爆发峰值 = 对单输出 × 数量 × 特殊倍率（仅雷霆 ×3）
      对单DPS  = 对单输出 ÷ 攻击间隔
    返回 (single_out, burst, dps)。
    """
    atk = float(atk or 0)
    ammo = float(ammo or 0)
    count = float(count or 0)
    interval = float(interval or 0)

    single_out = atk * ammo
    burst = single_out * count * BURST_MULTIPLIER.get(name, 1)
    dps = single_out / interval if interval else 0
    return single_out, burst, dps


def main(source_path=None):
    """把工作簿导出为 frontend/unit_data.json(.js)。

    source_path 为 None 时由 load_workbook 自动解析最新版本（累积全部历史变更，
    否则回退基准表）；显式传入（如 run_check 刚保存的新版 xlsx）则导出该文件。
    表内对单输出/爆发峰值/对单DPS 已下线，一律由 compute_derived 按原始列推算。
    """
    wb, ws, row_map, col_map = load_workbook(source_path, data_only=True)

    units = []
    for row in range(2, ws.max_row + 1):
        name = ws.cell(row=row, column=1).value
        if isinstance(name, str):
            name = name.strip()
        if not name or name in ("补充描述", ""):
            continue

        name = str(name)
        unit = {"name": name, "id": row - 1}
        for col_name_zh, col_idx in col_map.items():
            val = ws.cell(row=row, column=col_idx).value
            if val is not None:
                if isinstance(val, str):
                    val = val.strip()
                unit[col_name_zh] = val

        # 对空：表内已无此列，回退到 ANTI_AIR 清单（见文件头说明）
        if "对空" not in unit:
            unit["对空"] = ANTI_AIR.get(name, ANTI_AIR_DEFAULT)

        # 按规则推算 对单输出/爆发峰值/对单DPS
        so, burst, dps = compute_derived(
            name,
            unit.get("攻击力"),
            unit.get("弹药量"),
            unit.get("数量"),
            unit.get("攻击间隔"),
        )
        unit["对单输出"] = so
        unit["爆发峰值"] = burst
        unit["对单DPS"] = dps

        # 推导额外字段
        cost = unit.get("造价", 0)
        hp = unit.get("单体血量", 0)
        try:
            cost = int(cost) if cost else 0
            hp = int(hp) if hp else 0
        except (ValueError, TypeError):
            pass

        # 体型分类
        if cost >= 800:
            unit["体型"] = "超巨型"
        elif cost >= 400 or hp >= 40000:
            unit["体型"] = "巨型"
        elif cost >= 300 or hp >= 10000:
            unit["体型"] = "中型"
        else:
            unit["体型"] = "小型"

        # 移动类型：查显式清单，不再由 对空/移速 推断
        unit["移动类型"] = "飞行" if name in FLYING_UNITS else "地面"

        units.append(unit)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(units, f, ensure_ascii=False, indent=2)

    # Also output as JS for the frontend
    js_path = OUTPUT_PATH.replace('.json', '.js')
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("const RAW_UNIT_DATA = " + json.dumps(units, ensure_ascii=False) + ";")

    print(f"[OK] {len(units)} units → {OUTPUT_PATH}")
    print(f"[OK] JS data → {js_path}")
    return units


if __name__ == "__main__":
    main()
