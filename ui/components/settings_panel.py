"""
设置面板组件
包含所有时间间隔、重复次数等配置输入框
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    DEFAULT_INTERVAL_MS, DEFAULT_RECORD_INTERVAL,
    DEFAULT_HOLD_DURATION, DEFAULT_REPEAT_COUNT, DEFAULT_REPEAT_INTERVAL,
    PADDING_STANDARD, PADDING_SMALL,
    GRID_STICKY_W, GRID_STICKY_E
)


class SettingsPanel(ttk.Frame):
    """设置面板组件，包含所有配置输入框"""
    
    def __init__(self, parent):
        super().__init__(parent, padding=PADDING_STANDARD)
        
        # 存储所有变量的字典
        self.variables: Dict[str, tk.StringVar] = {}
        
        # 创建所有输入字段
        self._create_inputs()
    
    def _create_inputs(self):
        """创建所有输入字段"""
        # 点击间隔
        self._create_input_row(0, "点击间隔 (毫秒):", "interval_ms", 
                               str(DEFAULT_INTERVAL_MS))
        
        # 录制间隔
        self._create_input_row(1, "录制间隔 (毫秒):", "record_interval",
                               str(DEFAULT_RECORD_INTERVAL))
        
        # 按住持续时间
        self._create_input_row(2, "按住持续时间 (毫秒):", "hold_duration",
                               str(DEFAULT_HOLD_DURATION))
        
        # 重复次数
        self._create_input_row(3, "重复次数:", "repeat_count",
                               str(DEFAULT_REPEAT_COUNT))
        
        # 重复间隔
        self._create_input_row(4, "重复间隔 (毫秒):", "repeat_interval",
                               str(DEFAULT_REPEAT_INTERVAL))
    
    def _create_input_row(self, row: int, label_text: str, 
                          var_name: str, default_value: str):
        """
        创建一行输入控件
        
        Args:
            row: 行号
            label_text: 标签文本
            var_name: 变量名称（用于存储）
            default_value: 默认值
        """
        # 标签
        label = ttk.Label(self, text=label_text, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        label.grid(row=row, column=0, sticky=GRID_STICKY_W, pady=PADDING_SMALL)
        
        # 变量
        var = tk.StringVar(value=default_value)
        self.variables[var_name] = var
        
        # 输入框
        entry = ttk.Entry(self, textvariable=var)
        entry.grid(row=row, column=1, sticky=GRID_STICKY_E, 
                   pady=PADDING_SMALL, padx=(PADDING_STANDARD, 0))
        
        # 配置列权重使输入框可以扩展
        self.columnconfigure(1, weight=1)
    
    def get_values(self) -> Dict[str, int]:
        """
        获取所有输入值
        
        Returns:
            包含所有配置值的字典
        """
        values = {}
        for name, var in self.variables.items():
            try:
                values[name] = int(var.get())
            except ValueError:
                values[name] = 0  # 无效输入时返回 0
        return values
    
    def set_values(self, values: Dict[str, int]):
        """
        批量设置输入值
        
        Args:
            values: 包含配置值的字典
        """
        for name, value in values.items():
            if name in self.variables:
                self.variables[name].set(str(value))
    
    def get_value(self, name: str) -> int:
        """
        获取单个输入值
        
        Args:
            name: 变量名称
            
        Returns:
            输入值（整数）
        """
        if name not in self.variables:
            raise KeyError(f"未知的配置项：{name}")
        
        try:
            return int(self.variables[name].get())
        except ValueError:
            return 0
    
    def set_value(self, name: str, value: int):
        """
        设置单个输入值
        
        Args:
            name: 变量名称
            value: 值
        """
        if name not in self.variables:
            raise KeyError(f"未知的配置项：{name}")
        
        self.variables[name].set(str(value))
    
    def validate(self) -> tuple:
        """
        验证所有输入
        
        Returns:
            (是否有效，错误消息)
        """
        from config.validation import validate_time_inputs
        
        values = self.get_values()
        
        return validate_time_inputs(
            interval_ms=values.get('interval_ms', 0),
            record_interval=values.get('record_interval', 0),
            hold_duration=values.get('hold_duration', 0),
            repeat_count=values.get('repeat_count', 0),
            repeat_interval=values.get('repeat_interval', 0)
        )
    
    def reset_to_defaults(self):
        """重置为默认值"""
        self.set_values({
            'interval_ms': DEFAULT_INTERVAL_MS,
            'record_interval': DEFAULT_RECORD_INTERVAL,
            'hold_duration': DEFAULT_HOLD_DURATION,
            'repeat_count': DEFAULT_REPEAT_COUNT,
            'repeat_interval': DEFAULT_REPEAT_INTERVAL,
        })
