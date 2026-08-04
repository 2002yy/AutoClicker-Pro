"""
自动点击器 Pro - 主 UI 模块
纯 UI 层，不包含业务逻辑
"""

import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, Tuple

from config.constants import (
    APP_NAME, APP_VERSION, APP_WIDTH, APP_HEIGHT,
    APP_MIN_WIDTH, APP_MIN_HEIGHT,
    FONT_FAMILY, FONT_SIZE_TITLE, FONT_SIZE_SMALL,
    COLOR_PRIMARY, COLOR_DANGER, COLOR_SUCCESS, COLOR_DISABLED,
    PADDING_STANDARD, PADDING_LARGE, PADDING_SMALL,
    STATUS_READY,
    HOTKEY_START_STOP, HOTKEY_START_RECORDING,
    HOTKEY_STOP_RECORDING, HOTKEY_CANCEL, HOTKEY_HINT
)
from core.engine import ClickerEngine
from ui.components import SettingsPanel, ActionList, ControlButtons, StatusBar
from ui.theme import apply_win11_theme
from utils.hotkey_manager import HotkeyManager

# UI 事件队列轮询间隔（毫秒）
_UI_POLL_INTERVAL_MS = 50


class AutoClickerApp:
    """自动点击器主应用程序类（纯 UI）"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self._closing = False
        
        # 工作线程 -> 主线程的 UI 任务队列。
        # Tkinter 只能在主线程操作，后台线程一律通过该队列投递。
        self._ui_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        
        # 本窗口在屏幕上的矩形（含边框/标题栏），供录制过滤使用
        self._window_bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)
        
        # 窗口配置
        self._configure_window()
        
        # 创建引擎实例
        self.engine = ClickerEngine()
        self.engine.set_callbacks(
            on_status_change=self._on_engine_status_change,
            on_recording_update=self._on_engine_recording_update
        )
        # 录制时忽略落在本窗口内的点击（如点"停止录制"按钮）
        self.engine.ignore_click_predicate = self._is_point_in_own_window
        
        # 当前动作序列
        self._current_actions: list = []
        
        # 创建界面
        self._create_ui()
        
        # 绑定窗口内快捷键 + 全局快捷键
        self._bind_hotkeys()
        self.hotkey_manager: Optional[HotkeyManager] = None
        self._setup_global_hotkeys()
        
        # 跟踪窗口位置变化 + 启动 UI 队列轮询
        self.root.bind('<Configure>', self._on_window_configure)
        self.root.after(120, self._refresh_window_bounds)
        self.root.after(_UI_POLL_INTERVAL_MS, self._drain_ui_queue)
    
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
        
        # 配置网格权重（动作列表所在行才是可伸缩的主体区域）
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题 + 快捷键提示
        self._create_title(main_frame)
        
        # 设置面板
        self.settings_panel = SettingsPanel(main_frame)
        self.settings_panel.grid(row=2, column=0, sticky="ew", pady=(0, PADDING_STANDARD))
        
        # 控制按钮
        self.control_buttons = ControlButtons(main_frame)
        self.control_buttons.grid(row=3, column=0, sticky="ew", pady=(0, PADDING_STANDARD))
        
        # 设置按钮回调
        self.control_buttons.set_record_callback(self._on_record_click)
        self.control_buttons.set_click_callback(self._on_click_click)
        self.control_buttons.set_save_callback(self._on_save_click)
        self.control_buttons.set_load_callback(self._on_load_click)
        
        # 动作列表（占据剩余空间）
        self.action_list = ActionList(main_frame)
        self.action_list.grid(row=4, column=0, sticky="nsew", pady=(0, PADDING_STANDARD))
        
        # 状态栏
        self.status_bar = StatusBar(main_frame)
        self.status_bar.grid(row=5, column=0, sticky="ew")
    
    def _create_title(self, parent):
        """创建标题与快捷键提示"""
        title_label = ttk.Label(
            parent,
            text=f"{APP_NAME}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            foreground=COLOR_PRIMARY
        )
        title_label.grid(row=0, column=0, pady=(0, PADDING_SMALL))
        
        self.hotkey_hint_label = ttk.Label(
            parent,
            text=HOTKEY_HINT,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground=COLOR_DISABLED
        )
        self.hotkey_hint_label.grid(row=1, column=0, pady=(0, PADDING_LARGE))
    
    # ==================== 快捷键 ====================
    
    def _bind_hotkeys(self):
        """绑定窗口内快捷键（窗口获得焦点时生效）"""
        self.root.bind('<Escape>', lambda e: self._panic_stop())
    
    def _setup_global_hotkeys(self):
        """注册全局快捷键（窗口失焦时同样生效）"""
        manager = HotkeyManager()
        manager.register_hotkey(HOTKEY_START_STOP, self._hk_toggle_clicking)
        manager.register_hotkey(HOTKEY_START_RECORDING, self._hk_start_recording)
        manager.register_hotkey(HOTKEY_STOP_RECORDING, self._hk_stop_recording)
        manager.register_hotkey(HOTKEY_CANCEL, self._hk_panic_stop)
        
        try:
            manager.start()
            self.hotkey_manager = manager
        except Exception as e:
            # 某些环境（无输入权限 / 远程会话）无法注册全局钩子，
            # 此时降级为仅窗口内快捷键可用，不影响主功能。
            self.hotkey_manager = None
            self.status_bar.set_status(f"全局快捷键不可用（{e}），请使用界面按钮")
    
    # 以下 _hk_* 回调在 pynput 监听线程中被调用，必须转投主线程
    def _hk_toggle_clicking(self):
        self._dispatch_to_ui(self._on_click_click)
    
    def _hk_start_recording(self):
        self._dispatch_to_ui(self._start_recording_if_idle)
    
    def _hk_stop_recording(self):
        self._dispatch_to_ui(self._stop_recording_if_recording)
    
    def _hk_panic_stop(self):
        self._dispatch_to_ui(self._panic_stop)
    
    def _start_recording_if_idle(self):
        """如果未在录制则开始录制"""
        if not self.engine.is_recording:
            self._on_record_click()
    
    def _stop_recording_if_recording(self):
        """如果正在录制则停止"""
        if self.engine.is_recording:
            self.engine.stop_recording()
    
    def _panic_stop(self):
        """一键停止：同时终止录制与连点"""
        if self.engine.is_recording:
            self.engine.stop_recording()
        if self.engine.is_running:
            self.engine.stop_clicking()
    
    # ==================== 主线程调度 ====================
    
    def _dispatch_to_ui(self, func: Callable[[], None]):
        """从任意线程投递一个在主线程执行的任务"""
        if not self._closing:
            self._ui_queue.put(func)
    
    def _drain_ui_queue(self):
        """在主线程中消费 UI 任务队列"""
        while True:
            try:
                func = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except Exception as e:
                print(f"UI 任务执行失败：{e}")
        
        if not self._closing:
            self.root.after(_UI_POLL_INTERVAL_MS, self._drain_ui_queue)
    
    # ==================== 窗口位置追踪 ====================
    
    def _on_window_configure(self, event):
        """窗口移动/缩放时刷新自身屏幕矩形"""
        if event.widget is self.root:
            self._refresh_window_bounds()
    
    def _refresh_window_bounds(self):
        """缓存本窗口在屏幕上的矩形（含边框与标题栏）"""
        try:
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            # winfo_rootx/rooty 指向客户区左上角，减去 winfo_x/y 可得边框与标题栏厚度
            border = max(0, min(root_x - self.root.winfo_x(), 40))
            titlebar = max(0, min(root_y - self.root.winfo_y(), 120))
        except tk.TclError:
            return
        
        self._window_bounds = (
            root_x - border,
            root_y - titlebar,
            root_x + width + border,
            root_y + height + border,
        )
    
    def _is_point_in_own_window(self, x: int, y: int) -> bool:
        """判断屏幕坐标是否落在本程序窗口内（在监听线程中调用，只读缓存）"""
        left, top, right, bottom = self._window_bounds
        if right <= left or bottom <= top:
            return False
        return left <= x <= right and top <= y <= bottom
    
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
        # 通过队列转投主线程，避免跨线程直接操作 Tk
        self._dispatch_to_ui(lambda: self._update_status_ui(status))
    
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
        # 通过队列转投主线程，避免跨线程直接操作 Tk
        self._dispatch_to_ui(lambda: self._update_actions_list_ui(actions))
    
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
        self._closing = True
        
        if self.hotkey_manager is not None:
            try:
                self.hotkey_manager.stop()
            except Exception:
                pass
            self.hotkey_manager = None
        
        self.engine.cleanup()
        self.root.destroy()


def main():
    """程序入口函数"""
    root = tk.Tk()
    
    # 应用 Win11 风格主题（纯视觉）
    apply_win11_theme(root)
    
    # 自定义样式（主题兜底，确保状态色存在）
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
