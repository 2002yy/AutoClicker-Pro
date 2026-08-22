"""
宏库面板组件

下拉列出宏库中已保存的宏，支持快速加载 / 删除；
另附"导出 / 导入"入口（与任意位置 .enc 文件交换）。
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Optional

from config.constants import FONT_FAMILY, FONT_SIZE_NORMAL, PADDING_SMALL, PADDING_STANDARD


class MacroLibraryPanel(ttk.LabelFrame):
    """宏库面板：下拉选择 + 加载 / 删除，附导出 / 导入入口"""

    def __init__(self, parent,
                 on_load: Callable[[str], None],
                 on_delete: Callable[[str], None],
                 on_export: Callable[[], None],
                 on_import: Callable[[], None]):
        super().__init__(parent, text="宏库", padding=PADDING_STANDARD)
        self._on_load_cb = on_load
        self._on_delete_cb = on_delete
        self._on_export_cb = on_export
        self._on_import_cb = on_import

        # 宏名下拉框（占据剩余宽度）
        self.combo = ttk.Combobox(self, state='readonly')
        self.combo.grid(row=0, column=0, sticky='ew', padx=(0, PADDING_SMALL))
        self.columnconfigure(0, weight=1)

        self.load_button = ttk.Button(
            self, text="加载", command=self._load_selected,
            state=tk.DISABLED)
        self.load_button.grid(row=0, column=1, padx=(0, PADDING_SMALL))

        self.delete_button = ttk.Button(
            self, text="删除", command=self._delete_selected,
            state=tk.DISABLED)
        self.delete_button.grid(row=0, column=2, padx=(0, PADDING_SMALL))

        export_button = ttk.Button(
            self, text="导出", command=lambda: self._on_export_cb())
        export_button.grid(row=0, column=3, padx=(0, PADDING_SMALL))

        import_button = ttk.Button(
            self, text="导入", command=lambda: self._on_import_cb())
        import_button.grid(row=0, column=4)

    def _selected_name(self) -> Optional[str]:
        """当前选中的宏名；空返回 None"""
        name = self.combo.get().strip()
        return name or None

    def _load_selected(self):
        name = self._selected_name()
        if name:
            self._on_load_cb(name)

    def _delete_selected(self):
        name = self._selected_name()
        if name:
            self._on_delete_cb(name)

    def get_selected(self) -> Optional[str]:
        """供外部读取当前选中宏名"""
        return self._selected_name()

    def select(self, name: str):
        """把指定宏设为当前选中项（若存在于列表）"""
        if name in self.combo['values']:
            self.combo.set(name)

    def refresh(self, names: Iterable[str]):
        """刷新宏名列表；尽量保持原选中项，库空时禁用加载/删除按钮"""
        values = list(names)
        current = self.combo.get()
        self.combo['values'] = values

        has_items = bool(values)
        if not has_items:
            self.combo.set('')
        elif current in values:
            self.combo.set(current)
        else:
            self.combo.set(values[0])

        state = tk.NORMAL if has_items else tk.DISABLED
        self.load_button.config(state=state)
        self.delete_button.config(state=state)
