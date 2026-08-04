"""配置弹窗 —— 让用户填写 Deepseek API Key。

用 tkinter（Python 内置 GUI），免额外依赖。PyInstaller 打包时自动检测并打包。
实现要点：直接用根窗口当对话框（不用 Toplevel + withdraw + transient，
那套组合在 Windows 上会导致弹窗闪退）。
"""
import tkinter as tk
from tkinter import simpledialog


def ask_for_api_key() -> str:
    """弹出窗口让用户填写 Deepseek API Key。

    返回：
      - 用户输入并点击「保存」→ 返回输入的 key（已 strip）
      - 用户点击「跳过」/ 关闭窗口 / 留空保存 → 返回空字符串
    """
    result = {"key": ""}
    root = tk.Tk()
    root.title("Mechabellum 监控 — 配置 API Key")
    root.configure(bg="#f5f6f8")
    root.resizable(False, False)

    # 居中定位
    w, h = 480, 320
    root.update_idletasks()
    x = max((root.winfo_screenwidth() - w) // 2, 0)
    y = max((root.winfo_screenheight() - h) // 2, 0)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # 标题
    tk.Label(root, text="钢铁指挥官 · 平衡性监控",
             font=("Microsoft YaHei", 15, "bold"),
             bg="#f5f6f8", fg="#1a1a1a").pack(pady=(24, 6))
    tk.Label(root, text="请输入你的 Deepseek API Key",
             font=("Microsoft YaHei", 11),
             bg="#f5f6f8", fg="#333").pack()
    tk.Label(root, text="申请地址：https://platform.deepseek.com",
             font=("Microsoft YaHei", 9),
             bg="#f5f6f8", fg="#888").pack(pady=(2, 12))

    # 输入框（密码样式，可切换显示）
    entry = tk.Entry(root, width=44, show="*", font=("Consolas", 11))
    entry.pack(pady=6)
    entry.focus_set()

    def toggle_show():
        entry.config(show="" if entry.cget("show") == "*" else "*")

    tk.Button(root, text="显示/隐藏", font=("Microsoft YaHei", 9),
              relief="flat", command=toggle_show).pack()

    tk.Label(root, text="不填也可继续：仅检测公告并保存，不自动解析。\n下次启动仍会提示填写。",
             font=("Microsoft YaHei", 9), bg="#f5f6f8", fg="#999").pack(pady=(10, 4))

    def on_ok():
        result["key"] = entry.get().strip()
        root.destroy()

    def on_skip():
        result["key"] = ""
        root.destroy()

    btn_frame = tk.Frame(root, bg="#f5f6f8")
    btn_frame.pack(pady=(6, 0))
    tk.Button(btn_frame, text="保存", width=12, font=("Microsoft YaHei", 10),
              command=on_ok).pack(side="left", padx=8)
    tk.Button(btn_frame, text="跳过", width=12, font=("Microsoft YaHei", 10),
              command=on_skip).pack(side="left", padx=8)

    root.protocol("WM_DELETE_WINDOW", on_skip)
    entry.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_skip())

    try:
        root.mainloop()
    except Exception:
        # mainloop 异常时兜底：退回简单的 askstring
        try:
            root.destroy()
        except Exception:
            pass
        try:
            val = simpledialog.askstring("Mechabellum 配置",
                                         "请输入 Deepseek API Key（可留空跳过）：")
            result["key"] = (val or "").strip()
        except Exception:
            pass
    return result["key"]
