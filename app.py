#!/usr/bin/env python3
"""Mechabellum 监控 — 打包版入口。

PyInstaller 冻结后：
  1. 把内置资源（frontend/、基准 xlsx、.env 模板）复制到 exe 旁（首次运行）
  2. 启动服务器
  3. 自动打开浏览器

用户只需下载一个 exe，双击即用。API Key 由用户自己在 exe 旁的 .env 填写。
"""
import os
import shutil
import sys
import threading
import webbrowser


def get_base_dir() -> str:
    """exe 所在目录（冻结时）或脚本目录（源码运行时）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir() -> str:
    """PyInstaller 解压的内置资源目录；非冻结时同源码目录。"""
    return getattr(sys, "_MEIPASS", get_base_dir())


def ensure_resources(base: str) -> None:
    """首次运行时把内置资源复制到 exe 旁（可写目录），后续跳过。"""
    src = _bundle_dir()

    # 前端目录
    dest_frontend = os.path.join(base, "frontend")
    if not os.path.exists(dest_frontend):
        src_frontend = os.path.join(src, "frontend")
        if os.path.exists(src_frontend):
            shutil.copytree(src_frontend, dest_frontend)
            print("[初始化] 已创建 frontend/")

    # 基准数据表
    baseline = "钢铁指挥官兵种单位数据表7.29.xlsx"
    dest_xlsx = os.path.join(base, baseline)
    if not os.path.exists(dest_xlsx):
        src_xlsx = os.path.join(src, baseline)
        if os.path.exists(src_xlsx):
            shutil.copy2(src_xlsx, dest_xlsx)
            print("[初始化] 已创建基准数据表")

    # .env 模板（用户自填 Key）
    env_path = os.path.join(base, ".env")
    if not os.path.exists(env_path):
        src_env = os.path.join(src, ".env.default")
        if os.path.exists(src_env):
            shutil.copy2(src_env, env_path)
            print("[初始化] 已创建 .env 模板 —— 请填写你的 Deepseek API Key")
        else:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("DEEPSEEK_API_KEY=sk-在此填入你的DeepseekKey\n")
                f.write("DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic\n")
                f.write("DEEPSEEK_MODEL=deepseek-v4-flash\n")

    # 可写数据目录
    os.makedirs(os.path.join(base, "cache"), exist_ok=True)
    os.makedirs(os.path.join(base, "outputs"), exist_ok=True)


# 判断 key 是否已有效配置（占位符/空值视为未配置）
_PLACEHOLDER_HINTS = ("在此填入", "replace", "yourkey", "your_key", "xxx", "sk-这里")


def _read_env_key(env_path: str) -> str:
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _key_valid(key: str) -> bool:
    key = (key or "").strip()
    if not key:
        return False
    low = key.lower()
    return not any(t in low for t in _PLACEHOLDER_HINTS)


def _write_env_key(env_path: str, key: str) -> None:
    """把 key 写回 .env 的 DEEPSEEK_API_KEY 行（不存在则插入）。"""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("DEEPSEEK_API_KEY="):
            lines[i] = f"DEEPSEEK_API_KEY={key}"
            replaced = True
    if not replaced:
        lines.insert(0, f"DEEPSEEK_API_KEY={key}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def ensure_api_key(base: str) -> None:
    """未配置有效 key 时弹出窗口填写；跳过则保持离线模式。"""
    env_path = os.path.join(base, ".env")
    if _key_valid(_read_env_key(env_path)):
        return  # 已配置，不打扰
    try:
        from gui import ask_for_api_key
        key = ask_for_api_key()
        if key and _key_valid(key):
            _write_env_key(env_path, key)
            print("[配置] Deepseek API Key 已保存")
        else:
            print("[提示] 未配置 API Key，将仅检测公告不自动解析。")
    except Exception as e:
        print(f"[提示] 配置窗口打开失败（{e}）。可手动编辑 exe 旁的 .env 填写 DEEPSEEK_API_KEY。")


def main():
    base = get_base_dir()
    ensure_resources(base)
    ensure_api_key(base)

    # 让 config 解析 ROOT_DIR 到 exe 旁，再加载 server
    sys.path.insert(0, base)

    from config import SERVER_PORT
    import server

    server.start(port=SERVER_PORT)
    url = f"http://localhost:{SERVER_PORT}"
    print(f"\n========================================")
    print(f"  Mechabellum 平衡性监控已启动")
    print(f"  {url}")
    print(f"  按 Ctrl+C 停止")
    print(f"========================================")

    # 稍等服务器就绪再开浏览器
    def _open_browser():
        import time
        time.sleep(1.5)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()
        print("\n已停止。")


if __name__ == "__main__":
    main()
