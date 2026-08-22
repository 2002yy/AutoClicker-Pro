"""
动作列表组件
显示录制的宏动作序列
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable, Tuple

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    LISTBOX_HEIGHT, LISTBOX_WIDTH,
    PADDING_SMALL, GRID_STICKY_ALL
)


class ActionList(ttk.LabelFrame):
    """动作列表组件（标题框"动作序列"），显示宏动作并支持编辑"""

    def __init__(self, parent):
        super().__init__(parent, text="动作序列", padding=PADDING_SMALL)

        # 回调函数
        self.on_selection_change: Optional[Callable[[int], None]] = None

        # 行 -> 动作序列闭区间映射（折叠的轨迹行覆盖多个下标）
        self._row_ranges: List[Tuple[int, int]] = []

        # 编辑回调（由 App 注入；默认空操作）
        self._on_delete = lambda: None
        self._on_move_up = lambda: None
        self._on_move_down = lambda: None
        self._on_clear = lambda: None
        self._on_edit_coords = lambda: None

        # 创建组件
        self._create_widgets()

    def set_edit_callbacks(self, on_delete: Callable[[], None],
                           on_move_up: Callable[[], None],
                           on_move_down: Callable[[], None],
                           on_clear: Callable[[], None],
                           on_edit_coords: Optional[Callable[[], None]] = None):
        """注入编辑回调"""
        self._on_delete = on_delete
        self._on_move_up = on_move_up
        self._on_move_down = on_move_down
        self._on_clear = on_clear
        if on_edit_coords is not None:
            self._on_edit_coords = on_edit_coords

    def _create_widgets(self):
        """创建列表框、滚动条与编辑工具条"""
        # 编辑工具条
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        self.delete_button = ttk.Button(toolbar, text="删除选中",
                                        command=lambda: self._on_delete(),
                                        state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))

        self.edit_button = ttk.Button(toolbar, text="编辑坐标",
                                      command=lambda: self._on_edit_coords(),
                                      state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))

        self.move_up_button = ttk.Button(toolbar, text="上移",
                                         command=lambda: self._on_move_up(),
                                         state=tk.DISABLED)
        self.move_up_button.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))

        self.move_down_button = ttk.Button(toolbar, text="下移",
                                           command=lambda: self._on_move_down(),
                                           state=tk.DISABLED)
        self.move_down_button.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))

        self.clear_button = ttk.Button(toolbar, text="清空",
                                       command=lambda: self._on_clear(),
                                       state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, padx=(0, PADDING_SMALL))
        
        # 列表框框架
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表框
        self.listbox = tk.Listbox(
            list_frame,
            height=LISTBOX_HEIGHT,
            width=LISTBOX_WIDTH,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            selectmode=tk.SINGLE
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                  command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定滚动条
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # 绑定选择事件
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        # 配置框架扩展
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
    
    def _on_select(self, event):
        """处理选择事件"""
        selection = self.listbox.curselection()
        if selection and self.on_selection_change:
            index = selection[0]
            self.on_selection_change(index)
    
    def update_actions(self, actions: List[Dict[str, Any]]):
        """
        更新动作列表（连续的移动轨迹点折叠为一行）

        Args:
            actions: 宏动作列表
        """
        # 清空现有项目
        self.listbox.delete(0, tk.END)
        self._row_ranges = []

        i = 0
        n = len(actions)
        while i < n:
            action = actions[i]
            if action.get('kind', 'mouse') == 'move':
                # 收集连续移动点，折叠为一行
                j = i
                while j < n and actions[j].get('kind', 'mouse') == 'move':
                    j += 1
                run_len = j - i
                row_no = len(self._row_ranges) + 1
                if run_len > 1:
                    first_ts = float(actions[i].get('timestamp') or 0)
                    last_ts = float(actions[j - 1].get('timestamp') or 0)
                    label = (f"{row_no}. ⇢ 拖拽轨迹 ×{run_len} 点 "
                             f"@ {first_ts:.2f}s~{last_ts:.2f}s")
                else:
                    label = self._format_action(row_no, action)
                self._row_ranges.append((i, j - 1))
                self.listbox.insert(tk.END, label)
                i = j
            else:
                row_no = len(self._row_ranges) + 1
                self._row_ranges.append((i, i))
                self.listbox.insert(tk.END, self._format_action(row_no, action))
                i += 1

        # 录制时自动滚动到底部，让用户看到最新动作
        if actions:
            self.listbox.see(tk.END)

    def get_row_range(self, row_index: Optional[int]) -> Optional[Tuple[int, int]]:
        """
        把列表行号映射为动作序列下标的闭区间

        Args:
            row_index: 列表行号；None 直接返回 None

        Returns:
            (起始下标, 结束下标)（含两端）；越界返回 None
        """
        if row_index is None or not (0 <= row_index < len(self._row_ranges)):
            return None
        return self._row_ranges[row_index]

    def is_folded_row(self, row_index: Optional[int]) -> bool:
        """该行是否为折叠的轨迹段（覆盖多个动作）"""
        rng = self.get_row_range(row_index)
        return rng is not None and rng[1] > rng[0]
    
    def _format_action(self, index: int, action: Dict[str, Any]) -> str:
        """
        格式化动作为显示文本

        Args:
            index: 动作序号
            action: 动作字典

        Returns:
            格式化的字符串
        """
        action_type = action.get('action_type', 'press')
        timestamp = action.get('timestamp', 0)

        # 翻译动作类型
        action_names = {
            'press': '按下',
            'release': '释放',
            'tap': '点击'
        }
        action_name = action_names.get(action_type, action_type)

        # 组合键修饰键前缀，如 "Ctrl+"
        mods = action.get('modifiers') or []
        mod_prefix = ''.join(self._format_modifier(m) for m in mods)

        # 键盘组合键：如 "组合 [Ctrl+C]"
        if action.get('kind', 'mouse') == 'chord':
            key = action.get('key') or '?'
            display_key = key.upper() if len(key) == 1 else key
            return f"{index}. 组合 [{mod_prefix}{display_key}] @ {timestamp:.2f}s"

        # 键盘单键
        if action.get('kind', 'mouse') == 'key':
            key = action.get('key') or '?'
            return f"{index}. 按键 [{key}] {action_name} @ {timestamp:.2f}s"

        x = action.get('x', 0)
        y = action.get('y', 0)

        # 单条移动轨迹点
        if action.get('kind', 'mouse') == 'move':
            anchor = action.get('anchor_title')
            anchor_suffix = f" [窗:{anchor[:8]}]" if anchor else ""
            return f"{index}. 移动 ({x}, {y}) @ {timestamp:.2f}s{anchor_suffix}"

        button = action.get('button', 'left')

        # 翻译按钮名称
        button_names = {
            'left': '左键',
            'right': '右键',
            'middle': '中键',
            'x1': '侧键 1',
            'x2': '侧键 2'
        }
        button_name = button_names.get(button, button)
        combo_suffix = f" + {mod_prefix.rstrip('+')}组合" if mods else ""

        # 锚定窗口标记（回放时按该窗口当前位置重算坐标）
        anchor = action.get('anchor_title')
        anchor_suffix = f" [窗:{anchor[:8]}]" if anchor else ""

        return (f"{index}. ({x}, {y}) {button_name}{combo_suffix} "
                f"{action_name} @ {timestamp:.2f}s{anchor_suffix}")
    @staticmethod
    def _format_modifier(name: str) -> str:
        """修饰键名转显示名并带连接符（ctrl_l -> 'Ctrl+'）"""
        base = name.split('_', 1)[0].capitalize()
        label = {
            'Ctrl': 'Ctrl',
            'Alt': 'Alt',
            'Shift': 'Shift',
            'Cmd': 'Win',
        }.get(base, base)
        return f"{label}+"
    
    def get_selected_index(self) -> Optional[int]:
        """
        获取选中的索引
        
        Returns:
            选中的索引，如果没有选中则返回 None
        """
        selection = self.listbox.curselection()
        if selection:
            return selection[0]
        return None
    
    def get_selected_action(self, actions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        获取选中的动作
        
        Args:
            actions: 完整的动作列表
            
        Returns:
            选中的动作字典，如果没有选中或列表为空则返回 None
        """
        index = self.get_selected_index()
        if index is not None and 0 <= index < len(actions):
            return actions[index]
        return None
    
    def clear(self):
        """清空列表"""
        self.listbox.delete(0, tk.END)
    
    def get_count(self) -> int:
        """
        获取动作数量
        
        Returns:
            动作数量
        """
        return self.listbox.size()
    
    def enable_edit_buttons(self, has_actions: bool):
        """
        根据是否有动作启用/禁用编辑工具条

        Args:
            has_actions: 列表中是否存在动作
        """
        state = tk.NORMAL if has_actions else tk.DISABLED
        for btn in (self.delete_button, self.move_up_button,
                    self.move_down_button, self.clear_button):
            btn.config(state=state)

    def set_edit_coords_state(self, enabled: bool):
        """坐标编辑按钮独立启停（仅单个鼠标/移动类动作可选时可用）"""
        self.edit_button.config(
            state=tk.NORMAL if enabled else tk.DISABLED)

    def delete_selected(self):
        """删除选中的项目"""
        selection = self.listbox.curselection()
        if selection:
            self.listbox.delete(selection[0])
    
    def select_index(self, index: int):
        """
        选中指定索引的项目

        Args:
            index: 要选中的索引
        """
        if 0 <= index < self.listbox.size():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.see(index)
            # 程序化选中同样触发选择回调，保证依赖选中的状态同步
            self._on_select(None)
