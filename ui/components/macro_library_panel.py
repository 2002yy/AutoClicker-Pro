"""
宏库面板组件

下拉列出宏库中已保存的宏，支持快速加载 / 删除；
另附"导出 / 导入"入口（与任意位置 .enc 文件交换）。
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from config.constants import (FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
                              PADDING_SMALL, PADDING_STANDARD)


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

        # 真实宏名 <-> 展示文本（含动作数/保存时间）双向映射
        self._name_to_display = {}
        self._display_to_name = {}

        # 宏名下拉框（width 提供最小请求宽度；minsize 保证窄窗口下也不被压没）
        self.combo = ttk.Combobox(self, state="readonly", width=16)
        self.combo.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_SMALL))
        self.columnconfigure(0, weight=1, minsize=150)

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

        # 选中宏的元数据详情行
        self.detail_label = ttk.Label(self, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self.detail_label.grid(row=1, column=0, columnspan=5,
                               sticky=tk.W, pady=(PADDING_SMALL, 0))

    def set_detail(self, text: str):
        """更新选中宏的元数据说明行"""
        self.detail_label.config(text=text)

    def _selected_name(self) -> Optional[str]:
        """当前选中宏的真实名称（展示文本 -> 名称映射）；空返回 None"""
        display = self.combo.get().strip()
        if not display:
            return None
        return self._display_to_name.get(display, display)

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
        display = self._name_to_display.get(name)
        if display is not None:
            self.combo.set(display)

    def refresh(self, items):
        """刷新宏列表。

        Args:
            items: {真实宏名: 展示文本} 映射；尽量保持原选中项，
                   库空时禁用加载/删除按钮
        """
        self._items = dict(items or {})
        self._name_to_display = dict(self._items)
        self._display_to_name = {
            display: name for name, display in self._items.items()}
        values = list(self._items.values())
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
