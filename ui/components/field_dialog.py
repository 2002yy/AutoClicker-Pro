"""
小型模态编辑对话框

通用的"若干标签+输入框"表单，用于坐标微调等轻量编辑场景。
确认时逐字段校验，非法输入保持对话框打开并提示。
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple


class FieldDialog(tk.Toplevel):
    """模态字段编辑对话框。

    用法：
        dlg = FieldDialog(root, "编辑坐标", [("X", "100"), ("Y", "200")],
                          validators=[int_validator, int_validator])
        root.wait_window(dlg)
        if dlg.result: ...
    """

    def __init__(self, parent, title: str,
                 fields: List[Tuple[str, str]],
                 validators: Optional[list] = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Dict[str, str]] = None
        self._validators = validators or [None] * len(fields)

        self._vars: Dict[str, tk.StringVar] = {}
        for row, (label, initial) in enumerate(fields):
            ttk.Label(self, text=f"{label}:").grid(
                row=row, column=0, sticky=tk.W, padx=(12, 6), pady=8)
            var = tk.StringVar(master=self, value=str(initial))
            self._vars[label] = var
            entry = ttk.Entry(self, textvariable=var, width=12)
            entry.grid(row=row, column=1, padx=(0, 12), pady=8)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=len(fields), column=0, columnspan=2,
                          sticky=tk.E, padx=12, pady=(0, 10))
        ttk.Button(button_frame, text="确定", command=self._on_ok).pack(
            side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(
            side=tk.LEFT)

        self.error_label = ttk.Label(self, foreground="#C42B1C")
        self.error_label.grid(row=len(fields) + 1, column=0, columnspan=2,
                              sticky=tk.W, padx=12, pady=(0, 8))

        self.bind('<Return>', lambda _e: self._on_ok())
        self.bind('<Escape>', lambda _e: self.destroy())

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_visibility()
        self.focus_set()

    def _on_ok(self):
        values = {label: var.get().strip()
                  for label, var in self._vars.items()}
        for (label, _), validator in zip(self._vars.items(), self._validators):
            if validator is not None:
                error = validator(values[label])
                if error:
                    self.error_label.config(
                        text=f"{label}：{error}")
                    return
        self.result = values
        self.destroy()


def int_field(value: str) -> Optional[str]:
    """整数校验器：合法返回 None，否则返回错误消息"""
    try:
        int(value)
        return None
    except ValueError:
        return "必须是整数"
