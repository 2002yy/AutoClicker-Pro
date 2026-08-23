"""
新手教程对话框

首次启动自动弹出（settings.json 的 tutorial_seen 控制），
也可随时通过标题栏"新手教程"链接再次打开。
"""

import os
import webbrowser
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk

from config.constants import FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_TITLE

# 图文教程的在线地址（本地文档缺失时的兜底入口）
TUTORIAL_URL = ("https://github.com/2002yy/AutoClicker-Pro"
                "/blob/main/docs/TUTORIAL.md")

# 教程正文：(标题, 正文)
_SECTIONS = [
    ("三步上手（最简用法，无需录制）",
     "1. 设置点击间隔与重复次数（0=不限）\n"
     "2. 点击类型选 单击/双击/三击，位置选 跟随光标\n"
     "3. 按 F8 或点「开始点击」——鼠标在哪就在哪连点"),
    ("定点连点",
     "位置选「固定位置」→ 点「拾取坐标」倒计时 3 秒内把鼠标移到目标处，"
     "坐标自动填入 → F8 开始。适合挂机刷分、自动收菜。"),
    ("录制并回放操作序列",
     "按 F10 开始录制（正常做你的操作），F11 停止；"
     "点「开始点击」原速回放。拖拽轨迹、键盘组合键都会被完整记录。"),
    ("保存到宏库 / 窗口锚定",
     "「存入宏库」可给宏命名长期复用；带窗口锚定的宏在目标窗口移动后"
     "依然点到正确位置。快捷键可在下方自行修改，按钮标注同步更新。"),
]


def should_show_tutorial(settings: Optional[dict]) -> bool:
    """是否应在本次启动时弹出教程（纯函数，便于测试）"""
    if not settings:
        return True
    return not bool(settings.get('tutorial_seen'))


class TutorialDialog(tk.Toplevel):
    """新手教程窗口：正文 + 不再显示勾选 + 打开图文教程/开始使用按钮"""

    def __init__(self, master: tk.Tk,
                 on_dont_show: Optional[Callable[[], None]] = None):
        super().__init__(master)
        self.title("新手教程 - 快速上手")
        self.resizable(False, False)
        self.transient(master)

        self._on_dont_show = on_dont_show
        self.dont_show_var = tk.BooleanVar(master=self, value=False)

        container = ttk.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(container,
                          text="欢迎使用自动点击器 Pro",
                          font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        for i, (heading, body) in enumerate(_SECTIONS, start=1):
            h = ttk.Label(container, text=heading,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"))
            h.grid(row=i * 2 - 1, column=0, sticky="w", pady=(6, 1))
            b = ttk.Label(container, text=body,
                          font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                          foreground="#444444", wraplength=440,
                          justify="left")
            b.grid(row=i * 2, column=0, sticky="w")

        # 底部：不再显示 + 按钮
        bottom = ttk.Frame(container)
        bottom.grid(row=len(_SECTIONS) * 2 + 1, column=0,
                    sticky="ew", pady=(14, 0))
        check = ttk.Checkbutton(bottom, text="下次启动不再显示",
                                variable=self.dont_show_var)
        check.grid(row=0, column=0, sticky="w")
        doc_button = ttk.Button(bottom, text="打开图文教程",
                                command=self._open_doc)
        doc_button.grid(row=0, column=1, padx=8)
        start_button = ttk.Button(bottom, text="开始使用",
                                  command=self._close)
        start_button.grid(row=0, column=2)
        bottom.columnconfigure(0, weight=1)

        self.bind('<Escape>', lambda _e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.update_idletasks()
        self.center_over_master()

    def center_over_master(self):
        """居中于父窗口；无父窗口时居中屏幕"""
        try:
            self.update_idletasks()
            w, h = self.winfo_width(), self.winfo_height()
            mx = max(self.master.winfo_rootx()
                     + (self.master.winfo_width() - w) // 2, 0)
            my = max(self.master.winfo_rooty()
                     + (self.master.winfo_height() - h) // 3, 0)
            self.geometry(f"+{mx}+{my}")
        except tk.TclError:
            pass

    def _open_doc(self):
        """优先打开仓库内图文教程，缺失时打开在线版"""
        doc = Path(__file__).resolve().parents[2] / 'docs' / 'TUTORIAL.md'
        try:
            if doc.is_file():
                os.startfile(str(doc))  # noqa: 仅 Windows 目标
                return
        except OSError:
            pass
        try:
            webbrowser.open(TUTORIAL_URL)
        except Exception:
            pass

    def _close(self):
        if self.dont_show_var.get() and self._on_dont_show is not None:
            try:
                self._on_dont_show()
            except Exception:
                pass
        self.destroy()
