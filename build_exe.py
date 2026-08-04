#!/usr/bin/env python3
"""构建 Windows x64 单文件 exe。

不嵌入任何真实 API Key —— 打包的是 .env 模板（占位符），
下载者首次运行后在 exe 旁的 .env 中自填自己的 Deepseek Key。

用法：
  python build_exe.py

产出：dist/{EXE_NAME}.exe（VERSION 在文件顶部修改）
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(ROOT, "build_staging")
BASELINE = "钢铁指挥官兵种单位数据表7.29.xlsx"

# ===== 版本号（每次发布新版本时递增，exe 名为 MechaMv{版本}.exe）=====
VERSION = "1.0.3"
EXE_NAME = f"MechaMv{VERSION}"

# .env 模板（占位符，无真实 key）
ENV_TEMPLATE = """# ============================================
# Mechabellum 平衡性监控 — API 配置
# 请填入你自己的 Deepseek API Key 后保存，再重新点检查更新。
# 申请地址：https://platform.deepseek.com
# ============================================
DEEPSEEK_API_KEY=sk-在此填入你的DeepseekKey
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
DEEPSEEK_MODEL=deepseek-v4-flash
# 可选：修改端口
# SERVER_PORT=8800
"""


def main():
    print("=" * 60)
    print(f"构建 {EXE_NAME}.exe")
    print("=" * 60)

    # 1. 准备暂存目录（含内置资源）
    os.makedirs(STAGING, exist_ok=True)
    env_default = os.path.join(STAGING, ".env.default")
    with open(env_default, "w", encoding="utf-8") as f:
        f.write(ENV_TEMPLATE)
    print("[1/3] .env 模板已准备（占位符，无真实 key）")

    # 2. 校验内置资源存在
    for name in ("frontend/index.html", "frontend/unit_data.json", BASELINE):
        if not os.path.exists(os.path.join(ROOT, name)):
            print(f"[ERROR] 缺少内置资源: {name}")
            sys.exit(1)
    print("[2/3] 内置资源齐全")

    # 3. PyInstaller 构建（自动检测 UPX 压缩）
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--name", EXE_NAME,
        "--add-data", f"{os.path.join(ROOT, 'frontend')};frontend",
        "--add-data", f"{os.path.join(ROOT, BASELINE)};.",
        "--add-data", f"{env_default};.",
        "--hidden-import", "anthropic",
        # openpyxl 会条件导入 numpy（仅数组公式用），本项目用不到，排除以显著缩小体积
        "--exclude-module", "numpy",
        os.path.join(ROOT, "app.py"),
    ]
    # 若存在 upx.exe 则启用 UPX 压缩（可显著缩小体积）
    upx_bin = None
    for root_dir, _dirs, files in os.walk(os.path.join(ROOT, "upx")):
        if "upx.exe" in files:
            upx_bin = os.path.join(root_dir, "upx.exe")
            break
    if upx_bin:
        cmd += ["--upx-dir", os.path.dirname(upx_bin)]
        print("[3/3] 运行 PyInstaller (UPX 压缩)...")
    else:
        print("[3/3] 运行 PyInstaller (未找到 UPX)...")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print("[FAIL] PyInstaller 构建失败")
        sys.exit(1)

    exe = os.path.join(ROOT, "dist", f"{EXE_NAME}.exe")
    if os.path.exists(exe):
        size_mb = os.path.getsize(exe) / 1024 / 1024
        print(f"\n[OK] 构建完成: {exe}")
        print(f"     大小: {size_mb:.1f} MB")
        print(f"     下载者首次运行后，在 exe 旁的 .env 填自己的 Deepseek Key")
    else:
        print("[FAIL] 未找到输出 exe")
        sys.exit(1)


if __name__ == "__main__":
    main()
