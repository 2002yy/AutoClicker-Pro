"""
动作列表组件
显示录制的宏动作序列
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    LISTBOX_HEIGHT, LISTBOX_WIDTH,
    PADDING_SMALL, GRID_STICKY_ALL
)


class ActionList(ttk.Frame):
    """动作列表组件，显示录制的宏动作序列"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # 回调函数
        self.on_selection_change: Optional[Callable[[int], None]] = None
        
        # 创建组件
        self._create_widgets()
    
    def _create_widgets(self):
        """创建列表框和滚动条"""
        # 标签
        label = ttk.Label(self, text="录制的动作:", font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        label.pack(anchor=tk.W, pady=(0, PADDING_SMALL))
        
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
        更新动作列表
        
        Args:
            actions: 宏动作列表
        """
        # 清空现有项目
        self.listbox.delete(0, tk.END)
        
        # 添加新项目
        for i, action in enumerate(actions):
            action_str = self._format_action(i + 1, action)
            self.listbox.insert(tk.END, action_str)
    
    def _format_action(self, index: int, action: Dict[str, Any]) -> str:
        """
        格式化动作为显示文本
        
        Args:
            index: 动作序号
            action: 动作字典
            
        Returns:
            格式化的字符串
        """
        x = action.get('x', 0)
        y = action.get('y', 0)
        button = action.get('button', 'left')
        action_type = action.get('action_type', 'press')
        timestamp = action.get('timestamp', 0)
        
        # 翻译按钮名称
        button_names = {
            'left': '左键',
            'right': '右键',
            'middle': '中键',
            'x1': '侧键 1',
            'x2': '侧键 2'
        }
        button_name = button_names.get(button, button)
        
        # 翻译动作类型
        action_names = {
            'press': '按下',
            'release': '释放'
        }
        action_name = action_names.get(action_type, action_type)
        
        return f"{index}. ({x}, {y}) {button_name} {action_name} @ {timestamp:.2f}s"
    
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
