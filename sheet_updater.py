"""Excel 数据表更新模块"""
import openpyxl
import json
import os
import re
import shutil
from datetime import datetime
from config import (
    BASELINE_XLSX, OUTPUT_DIR, OUTPUT_PREFIX,
    COLUMN_MAP, CACHE_DIR, CHANGE_LOG_FILE,
    FIELD_ALIASES, UNIT_ALIASES, DERIVED_FIELDS
)


def ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def resolve_unit_name(unit: str):
    """公告单位名 → 表内单位名。无法归一化时返回 None。

    游戏内译名与表内译名不一致（公告写「漩涡」，表里叫「磁暴」），
    不归一化会被 apply_change 当成未知单位静默跳过。
    """
    if not unit:
        return None
    unit = str(unit).strip()
    if unit in UNIT_ALIASES:
        return UNIT_ALIASES[unit]
    return unit


def resolve_field_name(field: str):
    """公告属性名 → 表内列名。派生字段/未知属性返回 None。

    派生字段（对单输出/爆发峰值/对单DPS）在表内已下线，值口径是
    攻击力×弹药量，不能直接写入，调用方应登记到变更日志供人工复核。
    """
    if not field:
        return None
    field = str(field).strip()
    if field in DERIVED_FIELDS:
        return None
    if field in COLUMN_MAP:
        return field
    return FIELD_ALIASES.get(field)


def _resolve_newest_sheet() -> str:
    """解析最新数据表：outputs/ 下最近保存的 unit_data_v*.xlsx，若无则回退基准表。

    按文件修改时间取最新（版本号可能是 1.12 / 1.11.1.1a 等，不能按字典序比较），
    保证多次检查的变更在 outputs/ 中累积，而不是每次从基准表重建。
    """
    ensure_output_dir()
    candidates = [
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.startswith(OUTPUT_PREFIX) and f.endswith(".xlsx")
    ]
    if not candidates:
        print(f"[DATA] 数据源: 基准表 {os.path.basename(BASELINE_XLSX)}")
        return BASELINE_XLSX
    candidates.sort(key=os.path.getmtime)
    chosen = candidates[-1]
    # 打印实际数据源：这条日志缺失时，「改了数据表却没生效」只能靠猜
    print(f"[DATA] 数据源: outputs/{os.path.basename(chosen)}"
          f"（候选 {len(candidates)} 个）")
    return chosen


def load_workbook(path: str = None, data_only: bool = False) -> tuple:
    """加载 Excel 工作簿，返回 (workbook, sheet, row_map, col_map)

    path 为 None 时自动解析 outputs/ 下最新版本（实现跨版本变更累积），
    否则使用显式指定的文件。
    data_only=True 时读取公式的缓存计算结果（供 convert_to_json 导出）。
    注意：编辑/保存（balance_monitor）必须 data_only=False，否则公式会丢。
    row_map: {单位名: 行号}
    col_map: {列名: 列号}
    """
    path = path or _resolve_newest_sheet()
    wb = openpyxl.load_workbook(path, data_only=data_only)
    ws = wb.active

    # 建立列名→列号映射（第一行是表头）
    # 表头去掉首尾空格：手工维护的表里存在「 单体血量」「 溅射范围」这类带前导空格的写法，
    # 不 strip 会匹配不上 COLUMN_MAP 而被整列丢弃。
    col_map = {}  # {列名: 列号(1-based)}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if isinstance(header, str):
            header = header.strip()
        if header and header in COLUMN_MAP:
            col_map[header] = col

    # 建立单位名→行号映射
    row_map = {}  # {单位名: 行号(1-based)}
    for row in range(2, ws.max_row + 1):
        name = ws.cell(row=row, column=1).value
        if isinstance(name, str):
            name = name.strip()
        if name:
            row_map[str(name)] = row

    return wb, ws, row_map, col_map


def apply_change(ws, row_map: dict, col_map: dict,
                 unit: str, field: str, new_value: str) -> bool:
    """对工作表应用单条变更。返回是否成功。"""
    unit = resolve_unit_name(unit)
    if unit is None or unit not in row_map:
        print(f"  [SKIP] 未知单位: {unit}")
        return False

    cn_field = resolve_field_name(field)
    if cn_field is None or cn_field not in col_map:
        print(f"  [SKIP] 未知列名: {field}")
        return False

    row = row_map[unit]
    col = col_map[cn_field]

    old_val = ws.cell(row=row, column=col).value

    try:
        # 解析新值：可能是绝对值、百分比变化、或加减
        new_val = _compute_new_value(old_val, new_value)
    except Exception as e:
        print(f"  [ERROR] 计算新值失败: {e} | {unit}.{field}: {old_val} + {new_value}")
        return False

    ws.cell(row=row, column=col).value = new_val
    print(f"  [OK] {unit}.{field}: {old_val} → {new_val}")
    return True


def _compute_new_value(old_val, change_str: str):
    """根据变更描述计算新值"""
    s = str(change_str).strip()

    # 绝对值 + 括注: "1144 (+15%)" / "1370 (-10%)"
    # 模型常把相对变化括在绝对值后面。不剥掉括注会走「无法解析」分支，
    # 把整个字符串 "1144 (+15%)" 原样写进单元格。
    annot_match = re.match(r'^([+\-]?\d+\.?\d*)\s*[（(][^）)]*[）)]\s*$', s)
    if annot_match:
        s = annot_match.group(1)

    # 百分比: "+30%" / "-15%" / "30%" / "+30.5%"
    pct_match = re.match(r'^([+\-]?\d+\.?\d*)\s*%$', s)
    if pct_match and old_val is not None:
        pct = float(pct_match.group(1)) / 100.0
        old_num = float(str(old_val).replace(',', ''))
        return old_num * (1 + pct)

    # 加减: "+200" / "-50"
    add_match = re.match(r'^([+\-])(\d+\.?\d*)$', s)
    if add_match and old_val is not None:
        sign = 1 if add_match.group(1) == '+' else -1
        delta = float(add_match.group(2))
        old_num = float(str(old_val).replace(',', ''))
        return old_num + sign * delta

    # 绝对值: "300" / "300.5"
    abs_match = re.match(r'^(\d+\.?\d*)$', s)
    if abs_match:
        val = float(abs_match.group(1))
        if val == int(val):
            return int(val)
        return val

    # 无法解析：直接返回字符串
    return s


def save_new_sheet(wb, version: str) -> str:
    """保存新版 xlsx，返回文件路径"""
    ensure_output_dir()
    filename = f"{OUTPUT_PREFIX}{version}.xlsx"
    path = os.path.join(OUTPUT_DIR, filename)
    wb.save(path)
    print(f"\n[SAVED] {path}")
    return path


def log_changes(version: str, post_title: str, changes: list[dict],
                status: str = "applied"):
    """记录变更日志。

    status 取值：
      applied      — 有变动并已写入数据表
      no_changes   — 解析成功但公告无数值变动
      parse_failed — 解析失败，水位线不推进，下次重试
      test_server  — 测试服公告，不写入正式数据
      manual       — 人工手动更新
    每个状态都入库，日志选项卡能看见「这篇查过、结果是什么」，
    避免再出现「公告被静默跳过、数据没更新却无人知晓」。
    """
    ensure_output_dir()
    log = []
    if os.path.exists(CHANGE_LOG_FILE):
        with open(CHANGE_LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)

    log.append({
        "version": version,
        "title": post_title,
        "date": datetime.now().isoformat(),
        "status": status,
        "changes": changes,
    })

    with open(CHANGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"[LOG] 变更日志已更新 ({len(changes)} 条变动)")


def copy_baseline() -> str:
    """复制基准表到输出目录作为初始版本"""
    ensure_output_dir()
    dest = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}baseline.xlsx")
    shutil.copy2(BASELINE_XLSX, dest)
    print(f"[INIT] 基准表已复制到 {dest}")
    return dest


if __name__ == "__main__":
    # 测试：加载并显示表结构
    wb, ws, row_map, col_map = load_workbook()
    print(f"单位: {list(row_map.keys())[:5]}...")
    print(f"列: {list(col_map.keys())[:5]}...")

    # 测试变更应用
    test_changes = [
        {"unit": "爬虫", "field": "单体血量", "new": "300"},
    ]
    for c in test_changes:
        apply_change(ws, row_map, col_map, c["unit"], c["field"], c["new"])
    save_new_sheet(wb, "test")
