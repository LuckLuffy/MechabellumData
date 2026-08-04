#!/usr/bin/env python3
"""
Mechabellum 平衡性监控系统 — 主入口

用法：
  python balance_monitor.py          # 检查新公告，有平衡性调整则更新数据表
  python balance_monitor.py --init   # 初始化缓存（标记当前最新帖为已读）
  python balance_monitor.py --test   # 用当前 RSS 测试（不更新缓存）
  python balance_monitor.py --help   # 帮助

环境变量：
  ANTHROPIC_API_KEY     Claude API 密钥（用于解析公告内容）
  如未设置，公告将保存到 cache/parsed_posts/ 供手动分析
"""

import sys
import os

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BALANCE_KEYWORDS
from steam_fetcher import find_new_posts, get_latest_version, update_last_guid, fetch_rss
from change_parser import is_balance_update, parse_changes, format_changes_for_display
from sheet_updater import (
    load_workbook, apply_change, save_new_sheet, log_changes, copy_baseline
)


def print_banner():
    print("=" * 60)
    print("  Mechabellum 平衡性监控系统 v1.0")
    print("  Steam App 669330 | 钢铁指挥官")
    print("=" * 60)


def cmd_init():
    """初始化：标记当前最新帖为已读"""
    items = fetch_rss()
    if not items:
        print("[FAIL] 无法获取 RSS")
        return

    latest = items[0]
    update_last_guid(latest["guid"], latest["title"], latest["pub_date"])
    print(f"[INIT] 已标记最新帖: {latest['title']}")
    print(f"       发布日期: {latest['pub_date']}")
    print(f"       后续运行将只检测此帖之后的新公告。")
    # 同时复制基准表
    copy_baseline()


def cmd_test():
    """测试模式：显示 RSS 但不更新缓存"""
    items = fetch_rss()
    if not items:
        print("[FAIL] 无法获取 RSS")
        return

    print(f"\nRSS 共 {len(items)} 条公告\n")
    for i, item in enumerate(items[:5]):
        is_bal = is_balance_update(item)
        tag = "[平衡]" if is_bal else "[其他]"
        print(f"  {tag} {item['title']}")

        if is_bal:
            changes = parse_changes(item)
            print(format_changes_for_display(changes))
        print()


def _resolve_field(field: str):
    """把 Deepseek 返回的属性名解析为 Excel 列名。"""
    from config import COLUMN_MAP
    if field in COLUMN_MAP:
        return field
    for cn, en in COLUMN_MAP.items():
        if cn == field or en == field:
            return cn
    return None


def run_check() -> dict:
    """执行完整检查管线，返回结构化结果。"""
    result = {
        "new_posts": 0, "balance_posts": 0, "applied": 0,
        "version": None, "message": "", "changes": [],
    }

    posts = find_new_posts()
    if not posts:
        result["message"] = "无新公告。"
        return result

    result["new_posts"] = len(posts)
    latest_version = get_latest_version(posts) or posts[-1]["title"][:30]
    result["version"] = latest_version

    wb, ws, row_map, col_map = load_workbook()

    for post in posts:
        if not is_balance_update(post):
            continue

        result["balance_posts"] += 1
        changes = parse_changes(post)
        if not changes:
            continue

        applied = 0
        for change in changes:
            unit = change.get("unit", "")
            field = change.get("field", "")
            new_val = change.get("new", "")
            if not unit or not field:
                continue
            field_en = _resolve_field(field)
            if field_en is None:
                continue
            if apply_change(ws, row_map, col_map, unit, field_en, str(new_val)):
                applied += 1

        if applied > 0:
            save_new_sheet(wb, latest_version)
            log_changes(latest_version, post["title"], changes)
            result["applied"] += applied
            result["changes"].extend(changes)

    if posts:
        last = posts[-1]
        update_last_guid(last["guid"], last["title"], last["pub_date"])

    result["message"] = (
        f"应用 {result['applied']} 条变动至版本 {latest_version}。"
        if result["applied"] else "无平衡性数值变动需要更新。"
    )
    return result


def cmd_check():
    """主流程：检查新公告 → 解析 → 更新"""
    result = run_check()
    print(result["message"])


def main():
    print_banner()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--init":
            cmd_init()
        elif cmd == "--test":
            cmd_test()
        elif cmd in ("--help", "-h"):
            print(__doc__)
        else:
            print(f"未知参数: {cmd}")
            print(__doc__)
    else:
        cmd_check()


if __name__ == "__main__":
    main()
