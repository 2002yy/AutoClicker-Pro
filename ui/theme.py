"""
Win11 风格主题（纯视觉，不改变任何业务逻辑）

通过 ttk.Style 基于 'clam' 主题重建一套浅色、扁平、带强调色的视觉：
- Segoe UI 字体（Win11 默认）
- 浅灰中性背景 + 白色卡片
- 蓝(#0067C0)强调色主按钮
- 细边框、扁平圆角观感

所有配置都包在 try/except 中：任何一项在某些 Tk 发行版上不支持时静默跳过，
绝不影响功能。
"""

import tkinter as tk
from tkinter import ttk

# Win11 调色板
WIN11_BG = "#F3F3F3"          # 窗口背景（中性浅灰）
WIN11_SURFACE = "#FFFFFF"     # 卡片/输入框白底
WIN11_ACCENT = "#0067C0"      # 主强调蓝
WIN11_ACCENT_HOVER = "#005AAB"
WIN11_TEXT = "#1B1B1B"
WIN11_MUTED = "#5E5E5E"
WIN11_BORDER = "#D1D1D1"
WIN11_DANGER = "#C42B1C"
WIN11_SUCCESS = "#107C10"


def apply_win11_theme(root: tk.Tk) -> None:
    """给 Tk 根窗口应用 Win11 风格主题。"""
    try:
        style = ttk.Style(root)
        # 基于 clam：vista 主题会忽略 background 设置，无法上色；
        # clam 可控且跨平台表现一致。
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        # 全局默认字体与配色（Win11 默认 Segoe UI）
        try:
            style.configure('.', font=('Segoe UI', 10),
                            background=WIN11_BG, foreground=WIN11_TEXT)
        except tk.TclError:
            pass

        style.configure('TFrame', background=WIN11_BG)
        style.configure('TLabel', background=WIN11_BG, foreground=WIN11_TEXT)
        style.configure('TLabelframe', background=WIN11_BG,
                        bordercolor=WIN11_BORDER, relief='flat')
        style.configure('TLabelframe.Label',
                        background=WIN11_BG, foreground=WIN11_MUTED)

        # 输入框 / 列表：白底细边框
        style.configure('TEntry', fieldbackground=WIN11_SURFACE,
                        bordercolor=WIN11_BORDER, relief='solid', borderwidth=1)
        style.configure('TListbox', background=WIN11_SURFACE,
                        bordercolor=WIN11_BORDER, relief='solid')
        style.configure('TScrollbar', background=WIN11_BORDER,
                        troughcolor=WIN11_BG, relief='flat')

        # 普通按钮：白底 + 细边框（扁平观感）
        style.configure('TButton', background=WIN11_SURFACE,
                        foreground=WIN11_TEXT, bordercolor=WIN11_BORDER,
                        relief='solid', borderwidth=1, padding=(12, 6))
        style.map('TButton',
                  background=[('active', '#EAEAEA'), ('pressed', '#E0E0E0')],
                  bordercolor=[('active', WIN11_ACCENT)])

        # 强调按钮：蓝底白字
        style.configure('Accent.TButton', background=WIN11_ACCENT,
                        foreground='white', borderwidth=0,
                        relief='flat', padding=(12, 6))
        style.map('Accent.TButton',
                  background=[('active', WIN11_ACCENT_HOVER),
                              ('disabled', '#BFBFBF')])

        # 状态态按钮（录制/点击激活时使用前景色）
        style.configure('Danger.TButton', foreground=WIN11_DANGER)
        style.configure('Success.TButton', foreground=WIN11_SUCCESS)
        style.configure('Primary.TButton', foreground=WIN11_ACCENT)

        # 窗口背景
        try:
            root.configure(background=WIN11_BG)
        except tk.TclError:
            pass
    except Exception:
        # 主题失败绝不影响功能
        pass
