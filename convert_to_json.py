"""将 Excel 数据表转换为 JSON 供前端使用"""
import json
import os
from config import ROOT_DIR
from sheet_updater import load_workbook

OUTPUT_PATH = os.path.join(ROOT_DIR, "frontend", "unit_data.json")

# 地面单位但被"对空+速度快"规则误判为飞行的，强制标为地面
GROUND_FORCE = {"台风", "野马", "先知"}

# ===== 公式规则（用户特殊设计）=====
# 多武器单位：武器数（F 对单输出 = E攻击力 × 武器数）
MULTI_WEAPON = {
    "暴雨": 4, "鬼鳐": 2, "先知": 2,
    "恶灵": 4, "霸主": 4, "泰山": 4, "战争工厂": 2,
}
# 爆发峰值额外倍率（G = F × M × 倍率）
BURST_MULTIPLIER = {"雷霆": 3, "深渊": 10}
# 对单DPS 用爆发峰值/间隔 而非 对单输出/间隔 的单位
DPS_USE_BURST = {"深渊"}


def compute_derived(name: str, atk, count, interval,
                    single_out, burst, dps) -> tuple:
    """按规则兜底计算 对单输出/爆发峰值/对单DPS。

    表格里 F/G/H 是公式，openpyxl data_only 读缓存值；
    若缓存缺失（如 monitor 保存后未在 Excel 打开重算），按规则推算。
    返回 (single_out, burst, dps)。
    """
    weapon = MULTI_WEAPON.get(name, 1)
    atk = float(atk or 0)
    count = float(count or 0)
    interval = float(interval or 0)

    # 对单输出 F = 攻击力 × 武器数
    if single_out in (None, ""):
        single_out = atk * weapon
    else:
        single_out = float(single_out)

    # 爆发峰值 G = F × 数量 × 特殊倍率
    if burst in (None, ""):
        burst = single_out * count * BURST_MULTIPLIER.get(name, 1)
    else:
        burst = float(burst)

    # 对单DPS H = 对单输出/间隔（深渊 = 爆发峰值/间隔）
    if dps in (None, ""):
        base = burst if name in DPS_USE_BURST else single_out
        dps = base / interval if interval else 0
    else:
        dps = float(dps)

    return single_out, burst, dps


def main(source_path=None):
    """把工作簿导出为 frontend/unit_data.json(.js)。

    source_path 为 None 时由 load_workbook 自动解析最新版本（累积全部历史变更，
    否则回退基准表）；显式传入（如 run_check 刚保存的新版 xlsx）则导出该文件。
    用 data_only=True 读公式缓存值，缺失时按规则兜底计算。
    """
    wb, ws, row_map, col_map = load_workbook(source_path, data_only=True)

    units = []
    for row in range(2, ws.max_row + 1):
        name = ws.cell(row=row, column=1).value
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

        # 按规则兜底计算 对单输出/爆发峰值/对单DPS
        so, burst, dps = compute_derived(
            name,
            unit.get("攻击力"),
            unit.get("数量"),
            unit.get("攻击间隔"),
            unit.get("对单输出"),
            unit.get("爆发峰值"),
            unit.get("对单DPS"),
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

        # 移动类型（地面单位即使对空+速度快也不应标为飞行）
        if name in GROUND_FORCE:
            unit["移动类型"] = "地面"
        else:
            speed = unit.get("移速", 0)
            try:
                speed = int(speed) if speed else 0
            except (ValueError, TypeError):
                speed = 0
            unit["移动类型"] = "飞行" if unit.get("对空") and float(str(unit.get("对空", 0))) > 0.5 and speed > 8 else "地面"

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
