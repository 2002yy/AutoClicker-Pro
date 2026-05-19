"""
自动点击器 Pro - 主 UI 模块
纯 UI 层，不包含业务逻辑
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

from config.constants import (
    APP_NAME, APP_VERSION, APP_WIDTH, APP_HEIGHT,
    APP_MIN_WIDTH, APP_MIN_HEIGHT,
    FONT_FAMILY, FONT_SIZE_TITLE,
    COLOR_PRIMARY, COLOR_DANGER, COLOR_SUCCESS,
    PADDING_STANDARD, PADDING_LARGE,
    STATUS_READY
)
from core.engine import ClickerEngine
from ui.components import SettingsPanel, ActionList, ControlButtons, StatusBar


class AutoClickerApp:
    """自动点击器主应用程序类（纯 UI）"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        
        # 窗口配置
        self._configure_window()
        
        # 创建引擎实例
        self.engine = ClickerEngine()
        self.engine.set_callbacks(
            on_status_change=self._on_engine_status_change,
            on_recording_update=self._on_engine_recording_update
        )
        
        # 当前动作序列
        self._current_actions: list = []
        
        # 创建界面
        self._create_ui()
        
        # 绑定快捷键
        self._bind_hotkeys()
    
    def _configure_window(self):
        """配置窗口属性"""
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding=PADDING_STANDARD)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题
        self._create_title(main_frame)
        
        # 设置面板
        self.settings_panel = SettingsPanel(main_frame)
        self.settings_panel.grid(row=1, column=0, sticky="ew", pady=(0, PADDING_STANDARD))
        
        # 控制按钮
        self.control_buttons = ControlButtons(main_frame)
        self.control_buttons.grid(row=2, column=0, sticky="ew", pady=(0, PADDING_STANDARD))
        
        # 设置按钮回调
        self.control_buttons.set_record_callback(self._on_record_click)
        self.control_buttons.set_click_callback(self._on_click_click)
        self.control_buttons.set_save_callback(self._on_save_click)
        self.control_buttons.set_load_callback(self._on_load_click)
        
        # 动作列表
        self.action_list = ActionList(main_frame)
        self.action_list.grid(row=3, column=0, sticky="nsew", pady=(0, PADDING_STANDARD))
        
        # 状态栏
        self.status_bar = StatusBar(main_frame)
        self.status_bar.grid(row=4, column=0, sticky="ew")
    
    def _create_title(self, parent):
        """创建标题"""
        title_label = ttk.Label(
            parent,
            text=f"{APP_NAME}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            foreground=COLOR_PRIMARY
        )
        title_label.grid(row=0, column=0, pady=(0, PADDING_LARGE))
    
    def _bind_hotkeys(self):
        """绑定快捷键"""
        self.root.bind('<Escape>', lambda e: self._stop_recording_if_recording())
    
    def _stop_recording_if_recording(self):
        """如果正在录制则停止"""
        if self.engine.is_recording:
            self.engine.stop_recording()
    
    # ==================== 事件处理 ====================
    
    def _on_record_click(self):
        """录制按钮点击处理"""
        if not self.engine.is_recording:
            # 验证输入
            is_valid, error_msg = self.settings_panel.validate()
            if not is_valid:
                messagebox.showerror("输入错误", error_msg)
                return
            
            # 更新引擎配置
            self._update_engine_config()
            
            # 开始录制
            success = self.engine.start_recording()
            if success:
                self.status_bar.set_recording()
        else:
            # 停止录制
            self.engine.stop_recording()
    
    def _on_click_click(self):
        """点击按钮点击处理"""
        if not self.engine.is_running:
            # 验证输入
            is_valid, error_msg = self.settings_panel.validate()
            if not is_valid:
                messagebox.showerror("输入错误", error_msg)
                return
            
            # 检查是否有动作序列
            if len(self._current_actions) == 0:
                messagebox.showwarning("警告", "请先录制或加载一个宏序列")
                return
            
            # 更新引擎配置
            self._update_engine_config()

            # 传递动作序列到引擎
            self.engine.click_sequence = self._current_actions

            # 开始点击
            success = self.engine.start_clicking()
            if success:
                self.status_bar.set_clicking()
        else:
            # 停止点击
            self.engine.stop_clicking()
    
    def _on_save_click(self):
        """保存按钮点击处理"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".enc",
            filetypes=[("加密宏文件", "*.enc"), ("所有文件", "*.*")]
        )
        
        if filepath:
            try:
                self.status_bar.set_saving()
                self.engine.save_sequence(filepath)
                self.status_bar.set_success("保存成功")
            except Exception as e:
                self.status_bar.set_error(str(e))
                messagebox.showerror("保存失败", f"无法保存文件：{str(e)}")
    
    def _on_load_click(self):
        """加载按钮点击处理"""
        filepath = filedialog.askopenfilename(
            filetypes=[("加密宏文件", "*.enc"), ("所有文件", "*.*")]
        )
        
        if filepath:
            try:
                self.status_bar.set_loading()
                self.engine.load_sequence(filepath)
                self.status_bar.set_success("加载成功")
            except Exception as e:
                self.status_bar.set_error(str(e))
                messagebox.showerror("加载失败", f"无法加载文件：{str(e)}")
    
    def _update_engine_config(self):
        """更新引擎配置"""
        values = self.settings_panel.get_values()
        self.engine.update_config(
            interval_ms=values.get('interval_ms'),
            record_interval=values.get('record_interval'),
            hold_duration=values.get('hold_duration'),
            repeat_count=values.get('repeat_count'),
            repeat_interval=values.get('repeat_interval')
        )
    
    # ==================== 引擎回调 ====================
    
    def _on_engine_status_change(self, status: str):
        """引擎状态变化回调（在工作线程中调用）"""
        # 在主线程中更新 UI
        self.root.after(0, self._update_status_ui, status)
    
    def _update_status_ui(self, status: str):
        """更新状态 UI（在主线程中执行）"""
        if "正在录制" in status:
            self.status_bar.set_recording()
            self.control_buttons.update_recording_state(True)
        elif "录制已停止" in status:
            self.status_bar.set_recording_stopped()
            self.control_buttons.update_recording_state(False)
        elif "正在点击" in status:
            self.status_bar.set_clicking()
            self.control_buttons.update_clicking_state(True)
        elif "已停止" in status:
            self.status_bar.set_stopped()
            self.control_buttons.update_clicking_state(False)
        else:
            self.status_bar.set_status(status)
    
    def _on_engine_recording_update(self, actions: list):
        """引擎录制更新回调（在工作线程中调用）"""
        # 在主线程中更新 UI
        self.root.after(0, self._update_actions_list_ui, actions)
    
    def _update_actions_list_ui(self, actions: list):
        """更新动作列表 UI（在主线程中执行）"""
        self._current_actions = actions
        self.action_list.update_actions([action.to_dict() for action in actions])
        
        # 如果有动作，启用点击和保存按钮
        has_actions = len(actions) > 0
        self.control_buttons.enable_click_button(has_actions)
        self.control_buttons.enable_save_button(has_actions)
    
    def on_close(self):
        """窗口关闭事件"""
        self.engine.cleanup()
        self.root.destroy()


def main():
    """程序入口函数"""
    root = tk.Tk()
    
    # 自定义样式
    style = ttk.Style()
    style.configure("Danger.TButton", foreground=COLOR_DANGER)
    style.configure("Success.TButton", foreground=COLOR_SUCCESS)
    style.configure("Primary.TButton", foreground=COLOR_PRIMARY)
    
    # 创建应用
    app = AutoClickerApp(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
