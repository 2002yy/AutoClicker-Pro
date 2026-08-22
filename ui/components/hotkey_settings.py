"""
快捷键自定义组件
四个全局快捷键的查看与修改入口，含键名校验与重复检测。
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional, Tuple

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    PADDING_SMALL, PADDING_STANDARD,
)

# 动作标识 -> 显示名（顺序即界面顺序）
HOTKEY_FIELDS = [
    ('toggle', '启停连点'),
    ('start_recording', '开始录制'),
    ('stop_recording', '停止录制'),
    ('panic', '全部停止'),
]


def _pynput_key_names() -> set:
    """pynput 支持的特殊键名集合（惰性导入，避免组件加载期副作用）"""
    from pynput import keyboard
    return {k.name for k in keyboard.Key}


def is_valid_hotkey(value: str) -> bool:
    """校验单个键名或 '+' 组合（如 'f8'、'ctrl+shift+s'、'pause'）"""
    if not value:
        return False
    names = _pynput_key_names()
    for part in value.lower().split('+'):
        part = part.strip()
        if not part:
            return False
        if len(part) == 1 or part in names:
            continue
        return False
    return True


class HotkeySettings(ttk.LabelFrame):
    """全局快捷键设置区：2x2 输入框 + 应用按钮"""

    def __init__(self, parent, on_apply: Callable[[Dict[str, str]], None]):
        super().__init__(parent, text="全局快捷键", padding=PADDING_STANDARD)
        self._on_apply_cb = on_apply
        self.variables: Dict[str, tk.StringVar] = {}
        self.error_label: Optional[ttk.Label] = None

        # 两列布局：每组"标签+输入框"占两列
        for i, (action, label_text) in enumerate(HOTKEY_FIELDS):
            row, col = divmod(i, 2)
            base_col = col * 2

            label = ttk.Label(self, text=f"{label_text}:", font=(FONT_FAMILY, FONT_SIZE_NORMAL))
            label.grid(row=row, column=base_col, sticky=tk.W,
                       padx=(0, PADDING_SMALL), pady=PADDING_SMALL)

            var = tk.StringVar(master=self)
            self.variables[action] = var
            entry = ttk.Entry(self, textvariable=var, width=12)
            entry.grid(row=row, column=base_col + 1, sticky=tk.W + tk.E,
                       pady=PADDING_SMALL)

        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)

        apply_button = ttk.Button(self, text="应用快捷键",
                                  style='Accent.TButton',
                                  command=lambda: self._on_apply_cb(
                                      self.get_values()))
        apply_button.grid(row=len(HOTKEY_FIELDS) // 2, column=0,
                          columnspan=4, sticky=tk.E, pady=(PADDING_SMALL, 0))

    def set_values(self, mapping: Dict[str, str]):
        """填充当前生效的快捷键"""
        for action, key in mapping.items():
            if action in self.variables:
                self.variables[action].set(str(key))

    def get_values(self) -> Dict[str, str]:
        """获取归一化（小写、去空白）后的输入值"""
        return {
            action: var.get().strip().lower()
            for action, var in self.variables.items()
        }

    def validate(self) -> Tuple[bool, str]:
        """
        校验输入。

        Returns:
            (是否有效, 错误消息)
        """
        values = self.get_values()
        label_of = dict(HOTKEY_FIELDS)
        seen: Dict[str, str] = {}
        for action, label_text in HOTKEY_FIELDS:
            raw = values[action]
            if not raw:
                return False, f"{label_text} 的快捷键不能为空"
            if not is_valid_hotkey(raw):
                return False, (
                    f"{label_text} 的快捷键无效：{raw}\n"
                    "支持单键（如 f8 / pause / a）或组合键（如 ctrl+shift+s）"
                )
            if raw in seen:
                return False, (f"{label_text} 与 {seen[raw]} 的快捷键重复：{raw}")
            seen[raw] = label_text
        return True, ""

    def show_error(self, message: str):
        """在面板内显示校验错误（无需弹窗打断）"""
        if self.error_label is None:
            self.error_label = ttk.Label(self, foreground="#C42B1C")
            rows_used = (len(HOTKEY_FIELDS) + 1) // 2
            self.error_label.grid(row=rows_used + 1, column=0, columnspan=4,
                                  sticky=tk.W)
        self.error_label.config(text=message)

    def clear_error(self):
        """清除面板内错误提示"""
        if self.error_label is not None:
            self.error_label.config(text="")
