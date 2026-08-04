"""配置弹窗 —— 让用户填写 Deepseek API Key。

用 tkinter（Python 内置 GUI），免额外依赖。PyInstaller 打包时自动检测并打包。
"""
import tkinter as tk
from tkinter import ttk


def ask_for_api_key() -> str:
    """弹出窗口让用户填写 Deepseek API Key。

    返回：
      - 用户输入并点击「保存」→ 返回输入的 key（已 strip）
      - 用户点击「跳过」/ 关闭窗口 / 留空保存 → 返回空字符串
    """
    result = {"key": ""}

    root = tk.Tk()
    root.withdraw()  # 隐藏根窗口，只显示对话框

    win = tk.Toplevel(root)
    win.title("Mechabellum 监控 — 配置 API Key")
    win.configure(bg="#f5f6f8")
    win.resizable(False, False)
    win.geometry("480x300")

    # 居中
    win.update_idletasks()
    x = (win.winfo_screenwidth() - 480) // 2
    y = (win.winfo_screenheight() - 300) // 2
    win.geometry(f"+{x}+{y}")

    win.transient(root)
    win.grab_set()

    # 标题
    tk.Label(win, text="钢铁指挥官 · 平衡性监控",
             font=("Microsoft YaHei", 15, "bold"),
             bg="#f5f6f8", fg="#1a1a1a").pack(pady=(22, 6))

    # 说明
    tk.Label(win, text="请输入你的 Deepseek API Key",
             font=("Microsoft YaHei", 11),
             bg="#f5f6f8", fg="#333").pack()
    tk.Label(win, text="申请地址：https://platform.deepseek.com",
             font=("Microsoft YaHei", 9),
             bg="#f5f6f8", fg="#888").pack(pady=(2, 10))

    # 输入框（密码样式，点击可看）
    entry = tk.Entry(win, width=44, show="*", font=("Consolas", 11))
    entry.pack(pady=6)
    entry.focus_set()

    def toggle_show():
        entry.config(show="" if entry.cget("show") == "*" else "*")

    tk.Button(win, text="显示/隐藏", font=("Microsoft YaHei", 9),
              relief="flat", command=toggle_show).pack()

    # 提示
    tk.Label(win, text="不填也可继续：仅检测公告并保存，不自动解析。\n下次启动仍会提示填写。",
             font=("Microsoft YaHei", 9), bg="#f5f6f8", fg="#999").pack(pady=(8, 4))

    def on_ok():
        result["key"] = entry.get().strip()
        win.destroy()
        root.destroy()

    def on_skip():
        result["key"] = ""
        win.destroy()
        root.destroy()

    btn_frame = tk.Frame(win, bg="#f5f6f8")
    btn_frame.pack(pady=(4, 16))
    tk.Button(btn_frame, text="保存", width=12, font=("Microsoft YaHei", 10),
              command=on_ok).pack(side="left", padx=8)
    tk.Button(btn_frame, text="跳过", width=12, font=("Microsoft YaHei", 10),
              command=on_skip).pack(side="left", padx=8)

    win.protocol("WM_DELETE_WINDOW", on_skip)
    entry.bind("<Return>", lambda e: on_ok())
    win.bind("<Escape>", lambda e: on_skip())

    root.mainloop()
    return result["key"]
