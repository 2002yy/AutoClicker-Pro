"""
控制按钮组件
包含录制、点击、保存、加载等控制按钮
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    PADDING_STANDARD, PADDING_SMALL,
    STYLE_DANGER
)


class ControlButtons(ttk.Frame):
    """控制按钮组件，包含所有操作按钮"""
    
    def __init__(self, parent):
        super().__init__(parent, padding=PADDING_STANDARD)
        
        # 按钮状态
        self._is_recording = False
        self._is_clicking = False
        
        # 创建按钮
        self._create_buttons()
    
    def _create_buttons(self):
        """创建所有控制按钮"""
        # 录制按钮
        self.record_button = ttk.Button(
            self, 
            text="开始录制", 
            command=self._on_record_click
        )
        self.record_button.pack(side=tk.LEFT, padx=PADDING_SMALL)
        
        # 点击按钮
        self.click_button = ttk.Button(
            self,
            text="开始点击",
            command=self._on_click_click,
            state=tk.DISABLED
        )
        self.click_button.pack(side=tk.LEFT, padx=PADDING_SMALL)
        
        # 保存按钮
        self.save_button = ttk.Button(
            self,
            text="保存序列",
            command=self._on_save_click,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=PADDING_SMALL)
        
        # 加载按钮
        self.load_button = ttk.Button(
            self,
            text="加载序列",
            command=self._on_load_click
        )
        self.load_button.pack(side=tk.LEFT, padx=PADDING_SMALL)
    
    def set_record_callback(self, callback: Callable[[], None]):
        """设置录制按钮回调"""
        self._on_record_click = callback
    
    def set_click_callback(self, callback: Callable[[], None]):
        """设置点击按钮回调"""
        self._on_click_click = callback
    
    def set_save_callback(self, callback: Callable[[], None]):
        """设置保存按钮回调"""
        self._on_save_click = callback
    
    def set_load_callback(self, callback: Callable[[], None]):
        """设置加载按钮回调"""
        self._on_load_click = callback
    
    def update_recording_state(self, is_recording: bool):
        """
        更新录制状态
        
        Args:
            is_recording: 是否正在录制
        """
        self._is_recording = is_recording
        
        if is_recording:
            self.record_button.config(text="停止录制", style=STYLE_DANGER)
        else:
            self.record_button.config(text="开始录制", style="TButton")
    
    def update_clicking_state(self, is_clicking: bool):
        """
        更新点击状态
        
        Args:
            is_clicking: 是否正在点击
        """
        self._is_clicking = is_clicking
        
        if is_clicking:
            self.click_button.config(text="停止点击", style=STYLE_DANGER)
        else:
            self.click_button.config(text="开始点击", style="TButton")
    
    def enable_click_button(self, enabled: bool):
        """
        启用/禁用点击按钮
        
        Args:
            enabled: 是否启用
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.click_button.config(state=state)
    
    def enable_save_button(self, enabled: bool):
        """
        启用/禁用保存按钮
        
        Args:
            enabled: 是否启用
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.save_button.config(state=state)
    
    def reset(self):
        """重置所有按钮状态"""
        self.update_recording_state(False)
        self.update_clicking_state(False)
        self.enable_click_button(False)
        self.enable_save_button(False)
