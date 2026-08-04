"""将 Excel 数据表转换为 JSON 供前端使用"""
import json
import os
from config import ROOT_DIR
from sheet_updater import load_workbook

OUTPUT_PATH = os.path.join(ROOT_DIR, "frontend", "unit_data.json")

# 地面单位但被"对空+速度快"规则误判为飞行的，强制标为地面
GROUND_FORCE = {"台风", "野马", "先知"}


def main(source_path=None):
    """把工作簿导出为 frontend/unit_data.json(.js)。

    source_path 为 None 时由 load_workbook 自动解析最新版本（累积全部历史变更，
    否则回退基准表）；显式传入（如 run_check 刚保存的新版 xlsx）则导出该文件，
    确保 /api/data 反映最新已应用的数据。
    """
    wb, ws, row_map, col_map = load_workbook(source_path)

    units = []
    for row in range(2, ws.max_row + 1):
        name = ws.cell(row=row, column=1).value
        if not name or name in ("补充描述", ""):
            continue

        unit = {"name": str(name), "id": row - 1}
        for col_name_zh, col_idx in col_map.items():
            val = ws.cell(row=row, column=col_idx).value
            # 清理数值
            if val is not None:
                field = col_name_zh
                if isinstance(val, str):
                    val = val.strip()
                unit[field] = val

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
        _name = str(unit.get("name", ""))
        if _name in GROUND_FORCE:
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
