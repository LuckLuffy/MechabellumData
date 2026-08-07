#!/usr/bin/env python3
"""构建网页版静态站（web/）。

供 GitHub Pages 免费部署。生成：
  web/index.html        —— 纯静态数据页（内嵌数据，无服务器按钮，含更新横幅）
  web/unit_data.json    —— 原始数据（供玩家二次使用）
  web/updated_at.txt    —— 更新时间戳

用法：
  python build_web.py              # 本地构建（时间戳=当前时间）
  # CI 中由 GitHub Actions 调用，自动带运行时间
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_frontend import render_page, load_change_log

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(ROOT, "web")
DATA_PATH = os.path.join(ROOT, "frontend", "unit_data.json")


def get_updated_at() -> str:
    """时间戳：优先取 CI 提供的时间；本地则取当前时间。"""
    # GitHub Actions 不直接提供"本次运行时间"环境变量，用仓库当前时间或 UTC now。
    # 简单可靠：CI 上取 UTC 时间转北京时间显示。
    now = datetime.now(timezone.utc)
    return now.astimezone().strftime("%Y-%m-%d %H:%M")


def main():
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] 缺少数据文件: {DATA_PATH}")
        print("先运行 python balance_monitor.py 或 python convert_to_json.py 生成数据。")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    data_json = json.dumps(data, ensure_ascii=False)
    updated_at = get_updated_at()

    os.makedirs(WEB_DIR, exist_ok=True)
    html = render_page(data_json, web=True, updated_at=updated_at,
                       change_log=load_change_log())

    with open(os.path.join(WEB_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(WEB_DIR, "unit_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(WEB_DIR, "updated_at.txt"), "w", encoding="utf-8") as f:
        f.write(updated_at)

    print(f"[OK] 网页版已构建: {WEB_DIR}")
    print(f"     数据 {len(data)} 单位 · 更新时间 {updated_at}")


if __name__ == "__main__":
    main()
