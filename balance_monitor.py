#!/usr/bin/env python3
"""
Mechabellum 平衡性监控系统 — 主入口

用法：
  python balance_monitor.py          # 检查新公告，有平衡性调整则更新数据表
  python balance_monitor.py --init   # 初始化缓存（标记当前最新帖为已读）
  python balance_monitor.py --test   # 用当前 RSS 测试（不更新缓存）
  python balance_monitor.py --help   # 帮助

环境变量：
  DEEPSEEK_API_KEY      Deepseek API 密钥（用于解析公告内容）
  如未设置，公告将保存到 cache/parsed_posts/ 供手动分析
"""

import sys
import os
import threading

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BALANCE_KEYWORDS
from steam_fetcher import find_new_posts, get_latest_version, update_last_guid, fetch_rss
from change_parser import (
    is_balance_update, is_test_server, parse_changes,
    api_key_configured, format_changes_for_display
)
from sheet_updater import (
    load_workbook, apply_change, save_new_sheet, log_changes, copy_baseline,
    resolve_field_name, resolve_unit_name
)
from convert_to_json import main as export_to_json


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
    """把 Deepseek 返回的属性名解析为 Excel 列名（旧接口，保留供外部调用）。"""
    return resolve_field_name(field)


def _apply_changes(ws, row_map: dict, col_map: dict, changes: list[dict]) -> tuple:
    """应用一批变更，返回 (成功条数, 已写入的变更, 被跳过的变更)。

    被跳过的变更带 reason 字段，调用方要登记到变更日志——
    静默跳过正是 Update 2.0 丢数据时最难查的一环。
    """
    applied = 0
    done, skipped = [], []
    for change in changes:
        unit = change.get("unit", "")
        field = change.get("field", "")
        new_val = change.get("new", "")
        if not unit or not field:
            continue

        field_cn = resolve_field_name(field)
        if field_cn is None:
            skipped.append(dict(change, reason="派生字段/未知属性，需人工换算"))
            continue

        unit_cn = resolve_unit_name(unit)
        if unit_cn not in row_map:
            skipped.append(dict(change, reason=f"未收录单位（{unit_cn}）"))
            continue

        if apply_change(ws, row_map, col_map, unit, field_cn, str(new_val)):
            applied += 1
            done.append(change)
        else:
            skipped.append(dict(change, reason="写入失败"))
    return applied, done, skipped


_run_lock = threading.Lock()


def run_check() -> dict:
    """执行完整检查管线，返回结构化结果。

    内部持锁串行化，防止 server 启动线程与 POST /api/check 并发执行导致
    重复应用 / 缓存与 xlsx 竞争。run_check 不会递归调用自身，普通 Lock 即可。
    """
    with _run_lock:
        return _run_check_locked()


def _run_check_locked() -> dict:
    """run_check 的实际实现（调用方需持有 _run_lock）。"""
    result = {
        "new_posts": 0, "balance_posts": 0, "applied": 0,
        "version": None, "message": "", "changes": [],
    }

    posts = find_new_posts()
    if not posts:
        result["message"] = "无新公告。"
        return result

    result["new_posts"] = len(posts)
    # posts 按时间旧→新排列，版本号取末尾（最新）那篇
    latest_version = get_latest_version([posts[-1]]) or posts[-1]["title"][:30]
    result["version"] = latest_version

    wb, ws, row_map, col_map = load_workbook()
    parse_failed = False  # 有平衡帖解析失败则不推进水位线，下次整批重试

    for post in posts:
        if not is_balance_update(post):
            continue

        result["balance_posts"] += 1
        # 每篇用各自的版本号，避免整批共用一个版本号时 output 文件名串味
        post_version = get_latest_version([post]) or post["title"][:30]

        # 测试服公告不写正式数据（测试服数值经常不上线），但要留痕
        if is_test_server(post):
            log_changes(post_version, post["title"], [], status="test_server")
            continue

        changes = parse_changes(post)
        if changes is None:  # 解析失败：保留该帖，下次检查重试
            parse_failed = True
            log_changes(post_version, post["title"], [], status="parse_failed")
            continue
        if not changes:  # 解析成功但确实无数值变动
            log_changes(post_version, post["title"], [], status="no_changes")
            continue

        applied, done, skipped = _apply_changes(ws, row_map, col_map, changes)

        if applied > 0:
            saved_path = save_new_sheet(wb, post_version)
            # 重新导出 frontend/unit_data.json，让 /api/data 反映新版本
            export_to_json(source_path=saved_path)
            result["applied"] += applied
            result["changes"].extend(done)

        logged = done + skipped
        if not logged:
            status = "no_changes"
        elif applied:
            status = "applied"
        else:
            # 解析出内容却一条都没写进去（单位名/属性名对不上），
            # 必须显式登记，绝不能当成「无变动」混过去
            status = "skipped"
        log_changes(post_version, post["title"], logged, status=status)

    if posts and not parse_failed:
        last = posts[-1]
        update_last_guid(last["guid"], last["title"], last["pub_date"])

    if not api_key_configured():
        result["message"] = (
            "检测到平衡性公告，但未配置 Deepseek API Key。"
            "请在程序目录的 .env 文件中填写 DEEPSEEK_API_KEY 后重试。"
            "公告已保存到 cache/parsed_posts/ 供手动分析。"
        )
    elif result["applied"]:
        result["message"] = f"应用 {result['applied']} 条变动至版本 {latest_version}。"
    elif result["balance_posts"]:
        result["message"] = "有平衡性公告，但无数值变动需要更新（详情见日志选项卡）。"
    else:
        result["message"] = "有新公告，但均非平衡性调整。"
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
