"""
状态栏组件
显示应用程序当前状态
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    COLOR_DARK, COLOR_DANGER, COLOR_SUCCESS, COLOR_WARNING,
    PADDING_SMALL, STATUS_READY
)


class StatusBar(ttk.Frame):
    """状态栏组件，显示应用程序当前状态"""
    
    def __init__(self, parent):
        super().__init__(parent, padding=PADDING_SMALL)
        
        # 创建状态标签
        self._create_widgets()
        
        # 初始状态
        self.set_status(STATUS_READY)
    
    def _create_widgets(self):
        """创建状态标签"""
        self.status_label = ttk.Label(
            self,
            text=STATUS_READY,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            foreground=COLOR_DARK
        )
        self.status_label.pack(anchor=tk.W)
    
    def set_status(self, status: str, color: Optional[str] = None):
        """
        设置状态文本和颜色
        
        Args:
            status: 状态文本
            color: 状态颜色（可选，根据状态自动选择）
        """
        self.status_label.config(text=status)
        
        # 根据状态自动选择颜色
        if color is None:
            if "录制" in status or "点击" in status:
                color = COLOR_DANGER
            elif "成功" in status or "完成" in status:
                color = COLOR_SUCCESS
            elif "警告" in status or "错误" in status:
                color = COLOR_DANGER
            else:
                color = COLOR_DARK
        
        self.status_label.config(foreground=color)
    
    def set_ready(self):
        """设置为就绪状态"""
        self.set_status(STATUS_READY, COLOR_DARK)
    
    def set_recording(self):
        """设置为录制状态"""
        self.set_status("正在录制... 按 ESC 停止", COLOR_DANGER)
    
    def set_recording_stopped(self):
        """设置为录制停止状态"""
        self.set_status("录制已停止", COLOR_DARK)
    
    def set_clicking(self):
        """设置为点击状态"""
        self.set_status("正在点击...", COLOR_DANGER)
    
    def set_stopped(self):
        """设置为停止状态"""
        self.set_status("已停止", COLOR_DARK)
    
    def set_loading(self):
        """设置为加载状态"""
        self.set_status("加载中...", COLOR_WARNING)
    
    def set_saving(self):
        """设置为保存状态"""
        self.set_status("保存中...", COLOR_WARNING)
    
    def set_error(self, error_message: str):
        """
        设置错误状态
        
        Args:
            error_message: 错误消息
        """
        self.set_status(f"错误：{error_message}", COLOR_DANGER)
    
    def set_success(self, success_message: str):
        """
        设置成功状态
        
        Args:
            success_message: 成功消息
        """
        self.set_status(success_message, COLOR_SUCCESS)
    
    def clear(self):
        """清空状态"""
        self.status_label.config(text="")
