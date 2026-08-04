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


def main():
    base = get_base_dir()
    ensure_resources(base)

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
