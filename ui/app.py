"""
自动点击器 Pro - 主 UI 模块
纯 UI 层，不包含业务逻辑
"""

import queue
import gc
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Callable, Optional, Tuple

from config.constants import (
    APP_NAME, APP_VERSION, APP_WIDTH, APP_HEIGHT,
    APP_MIN_WIDTH, APP_MIN_HEIGHT,
    FONT_FAMILY, FONT_SIZE_TITLE, FONT_SIZE_SMALL,
    COLOR_PRIMARY, COLOR_DANGER, COLOR_SUCCESS, COLOR_DISABLED,
    PADDING_STANDARD, PADDING_LARGE, PADDING_SMALL,
    STATUS_READY,
    HOTKEY_START_STOP, HOTKEY_START_RECORDING,
    HOTKEY_STOP_RECORDING, HOTKEY_CANCEL,
)
from config import macro_library
from config.settings_store import load_settings, save_settings
from config.validation import validate_macro_sequence
from core.engine import ClickerEngine, EngineEvent
from core.macros import ClickAction
from ui.components import SettingsPanel, ActionList, ControlButtons, StatusBar
from ui.components.hotkey_settings import HotkeySettings, HOTKEY_FIELDS
from ui.components.macro_library_panel import MacroLibraryPanel
from ui.theme import apply_win11_theme
from utils.hotkey_manager import HotkeyManager

# UI 事件队列轮询间隔（毫秒）
_UI_POLL_INTERVAL_MS = 50

# 各动作的默认全局快捷键（可被 settings.json 覆盖）
DEFAULT_HOTKEYS = {
    'toggle': HOTKEY_START_STOP,
    'start_recording': HOTKEY_START_RECORDING,
    'stop_recording': HOTKEY_STOP_RECORDING,
    'panic': HOTKEY_CANCEL,
}


def _display_key(key: str) -> str:
    """键名转展示文本（'f8'->'F8'，单字符大写，其余首字母大写）"""
    key = key.strip().lower()
    if len(key) == 1:
        return key.upper()
    return key.upper() if key.upper() in ("ESC",) else key.capitalize()


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

        # 挂起的 root.after 定时器 ID：关闭时统一取消，
        # 避免销毁后回调触发 Tcl "invalid command name" 后台错误
        self._pending_afters: set = set()
        
        # 窗口配置
        self._configure_window()
        
        # 创建引擎实例
        self.engine = ClickerEngine()
        self.engine.set_callbacks(
            on_status_change=self._on_engine_status_change,
            on_recording_update=self._on_engine_recording_update,
            on_engine_event=self._on_engine_event
        )
        # 录制时忽略落在本窗口内的点击（如点"停止录制"按钮）
        self.engine.ignore_click_predicate = self._is_point_in_own_window

        # 当前动作序列
        self._current_actions: list = []

        # 生效中的全局快捷键（settings.json 覆盖默认值）
        self.hotkeys: dict = dict(DEFAULT_HOTKEYS)
        saved = load_settings().get('hotkeys')
        if isinstance(saved, dict):
            for action in DEFAULT_HOTKEYS:
                value = saved.get(action)
                if isinstance(value, str) and value.strip():
                    self.hotkeys[action] = value.strip().lower()

        # 创建界面
        self._create_ui()
        
        # 绑定窗口内快捷键 + 全局快捷键
        self._bind_hotkeys()
        self.hotkey_manager: Optional[HotkeyManager] = None
        self._setup_global_hotkeys()
        
        # 跟踪窗口位置变化 + 启动 UI 队列轮询
        self.root.bind('<Configure>', self._on_window_configure)
        self._schedule_after(120, self._refresh_window_bounds)
        self._schedule_after(_UI_POLL_INTERVAL_MS, self._drain_ui_queue)

    def _schedule_after(self, ms: int, func: Callable[[], None]):
        """root.after 的受管版本：登记定时器 ID 供 on_close 统一取消；
        触发后自动从集合移除，避免集合随运行时间无限增长"""
        def _wrapped():
            self._pending_afters.discard(after_id)
            func()

        try:
            after_id = self.root.after(ms, _wrapped)
            self._pending_afters.add(after_id)
        except tk.TclError:
            pass  # 窗口已销毁时静默放弃
    
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
        main_frame.rowconfigure(6, weight=1)

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

        # 宏库面板（加载/删除/导出/导入）
        self.library_panel = MacroLibraryPanel(
            main_frame,
            on_load=self._on_library_load,
            on_delete=self._on_library_delete,
            on_export=self._on_export_click,
            on_import=self._on_import_click,
        )
        self.library_panel.grid(row=4, column=0, sticky="ew",
                                pady=(0, PADDING_STANDARD))
        self._refresh_macro_library()

        # 全局快捷键自定义区
        self.hotkey_settings = HotkeySettings(main_frame,
                                              on_apply=self._apply_hotkeys)
        self.hotkey_settings.set_values(self.hotkeys)
        self.hotkey_settings.grid(row=5, column=0, sticky="ew",
                                  pady=(0, PADDING_STANDARD))

        # 动作列表（占据剩余空间）
        self.action_list = ActionList(main_frame)
        self.action_list.grid(row=6, column=0, sticky="nsew", pady=(0, PADDING_STANDARD))
        self.action_list.set_edit_callbacks(
            on_delete=self._on_delete_action,
            on_move_up=lambda: self._on_move_action(-1),
            on_move_down=lambda: self._on_move_action(1),
            on_clear=self._on_clear_actions,
        )
        self.action_list.on_selection_change = self._on_list_selection_change

        # 状态栏
        self.status_bar = StatusBar(main_frame)
        self.status_bar.grid(row=7, column=0, sticky="ew")

    def _refresh_macro_library(self):
        """重新列举宏库并刷新下拉框"""
        self.library_panel.refresh(macro_library.list_macros())

    def _hotkey_hint_text(self) -> str:
        """根据当前生效的快捷键动态生成提示文案"""
        labels = dict(HOTKEY_FIELDS)
        parts = [f"{_display_key(self.hotkeys[action])} {labels[action]}"
                 for action, _ in HOTKEY_FIELDS]
        return " | ".join(parts)
    
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
            text=self._hotkey_hint_text(),
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground=COLOR_DISABLED
        )
        self.hotkey_hint_label.grid(row=1, column=0, pady=(0, PADDING_LARGE))
    
    # ==================== 快捷键 ====================
    
    def _bind_hotkeys(self):
        """绑定窗口内快捷键（窗口获得焦点时生效）"""
        self.root.bind('<Escape>', lambda e: self._panic_stop())
    
    def _setup_global_hotkeys(self):
        """按当前生效的快捷键映射注册全局热键（窗口失焦时同样生效）"""
        manager = HotkeyManager()
        manager.register_hotkey(self.hotkeys['toggle'], self._hk_toggle_clicking)
        manager.register_hotkey(self.hotkeys['start_recording'], self._hk_start_recording)
        manager.register_hotkey(self.hotkeys['stop_recording'], self._hk_stop_recording)
        manager.register_hotkey(self.hotkeys['panic'], self._hk_panic_stop)

        try:
            manager.start()
            self.hotkey_manager = manager
        except Exception as e:
            # 某些环境（无输入权限 / 远程会话）无法注册全局钩子，
            # 此时降级为仅窗口内快捷键可用，不影响主功能。
            self.hotkey_manager = None
            self.status_bar.set_status(f"全局快捷键不可用（{e}），请使用界面按钮")

        # 录制时跳过这些控制键（含用户自定义后的键名）
        self.engine.set_skip_key_names(
            list(self.hotkeys.values()) + [HOTKEY_CANCEL]
        )

    def _apply_hotkeys(self, values: dict):
        """应用自定义快捷键：校验 -> 重建监听 -> 更新引擎跳过集与提示 -> 持久化"""
        ok, error_msg = self.hotkey_settings.validate()
        if not ok:
            self.hotkey_settings.show_error(error_msg)
            return
        self.hotkey_settings.clear_error()

        # 停旧监听、按新映射整体重建，避免部分注册的中间状态
        if self.hotkey_manager is not None:
            try:
                self.hotkey_manager.stop()
            except Exception:
                pass
            self.hotkey_manager = None

        self.hotkeys = {action: values[action] for action, _ in HOTKEY_FIELDS}
        self._setup_global_hotkeys()

        # 提示文案随实际按键更新；持久化失败不影响本次会话
        self.hotkey_hint_label.config(text=self._hotkey_hint_text())
        if save_settings({'hotkeys': self.hotkeys}):
            self.status_bar.set_success("快捷键已更新并保存")
        else:
            self.status_bar.set_success("快捷键已更新（写入设置文件失败，重启后失效）")
    
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
    
    def _drain_ui_queue(self, *_args):
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
            self._schedule_after(_UI_POLL_INTERVAL_MS, self._drain_ui_queue)
    
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
        """保存当前序列到宏库（重名需确认覆盖）"""
        if len(self.engine.get_sequence()) == 0:
            messagebox.showwarning("警告", "没有可保存的动作序列")
            return

        name = simpledialog.askstring(
            "保存到宏库", "宏名称：", parent=self.root)
        if name is None:
            return  # 用户取消
        clean = macro_library.sanitize_name(name)
        if not clean:
            messagebox.showerror("保存失败", "宏名称无效")
            return

        if macro_library.macro_exists(clean) and not messagebox.askyesno(
                "覆盖确认", f"宏“{clean}”已存在，是否覆盖？"):
            return

        try:
            actions_data = [a.to_dict() for a in self.engine.get_sequence()]
            is_valid, error_msg = validate_macro_sequence(actions_data)
            if not is_valid:
                raise ValueError(error_msg)
            used_name = macro_library.save_to_library(clean, actions_data)
            self._refresh_macro_library()
            self.library_panel.select(used_name)
            self.status_bar.set_success(f"已保存到宏库：{used_name}")
        except Exception as e:
            self.status_bar.set_error(str(e))
            messagebox.showerror("保存失败", f"无法保存到宏库：{e}")

    def _on_library_load(self, name: str):
        """从宏库加载选中的宏"""
        try:
            data = macro_library.load_from_library(name)
            is_valid, error_msg = validate_macro_sequence(data)
            if not is_valid:
                raise ValueError(error_msg)
            self.engine.click_sequence = [
                ClickAction.from_dict(d) for d in data]
            self._refresh_actions_ui(select=0)
            self.status_bar.set_success(f"已加载宏：{name}")
        except Exception as e:
            self.status_bar.set_error(str(e))
            messagebox.showerror("加载失败", f"无法加载宏“{name}”：{e}")

    def _on_library_delete(self, name: str):
        """删除宏库中选中的宏（需确认）"""
        if not messagebox.askyesno(
                "删除宏", f"确定删除宏库中的“{name}”？此操作不可恢复。"):
            return
        if macro_library.delete_macro(name):
            self._refresh_macro_library()
            self.status_bar.set_success(f"已删除宏：{name}")
        else:
            messagebox.showerror("删除失败", f"无法删除宏“{name}”")

    def _on_export_click(self):
        """把当前序列导出为任意位置的 .enc 文件"""
        if len(self.engine.get_sequence()) == 0:
            messagebox.showwarning("警告", "没有可导出的动作序列")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".enc",
            filetypes=[("加密宏文件", "*.enc"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
        try:
            self.engine.save_sequence(filepath)
            self.status_bar.set_success(f"已导出：{filepath}")
        except Exception as e:
            self.status_bar.set_error(str(e))
            messagebox.showerror("导出失败", f"无法导出文件：{e}")

    def _on_import_click(self):
        """从任意位置的 .enc 文件导入序列到编辑区"""
        filepath = filedialog.askopenfilename(
            filetypes=[("加密宏文件", "*.enc"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
        try:
            self.engine.load_sequence(filepath)
            self._refresh_actions_ui(select=0)
            self.status_bar.set_success(f"已导入：{filepath}")
        except Exception as e:
            self.status_bar.set_error(str(e))
            messagebox.showerror("导入失败", f"无法导入文件：{e}")
    
    def _update_engine_config(self):
        """更新引擎配置"""
        values = self.settings_panel.get_values()
        self.engine.update_config(
            interval_ms=values.get('interval_ms'),
            record_interval=values.get('record_interval'),
            hold_duration=values.get('hold_duration'),
            repeat_count=values.get('repeat_count'),
            repeat_interval=values.get('repeat_interval'),
            start_delay_s=values.get('start_delay_s'),
            auto_stop_s=values.get('auto_stop_s')
        )

    # ==================== 序列编辑 ====================

    def _refresh_actions_ui(self, select: Optional[int] = None):
        """从引擎读取序列并刷新列表与按钮状态（编辑操作后调用）"""
        actions = self.engine.get_sequence()
        self._update_actions_list_ui(actions)
        if select is not None and 0 <= select < len(actions):
            self.action_list.select_index(select)

    def _on_delete_action(self):
        """删除当前选中行对应的动作；折叠的轨迹行删除整段"""
        row_index = self.action_list.get_selected_index()
        rng = self.action_list.get_row_range(row_index)
        if rng is None:
            return
        start, end = rng
        removed = (self.engine.remove_range(start, end) if end > start
                   else (1 if self.engine.remove_action(start) else 0))
        if not removed:
            return
        remaining_rows = len(self.engine.get_sequence())
        self._refresh_actions_ui(select=min(start, remaining_rows - 1))

    def _on_move_action(self, delta: int):
        """把选中的动作上移(-1)/下移(+1)，保持其选中状态。

        折叠的轨迹段不支持整体移动（拖拽顺序即录制顺序）。
        """
        row_index = self.action_list.get_selected_index()
        if row_index is None:
            return
        if self.action_list.is_folded_row(row_index):
            self.status_bar.set_status("拖拽轨迹段不支持整体移动，如需调整请删除后重录")
            return
        rng = self.action_list.get_row_range(row_index)
        if rng is None:
            return
        index = rng[0]
        target = index + delta
        if not self.engine.move_action(index, target):
            return
        self._refresh_actions_ui(select=target)

    def _on_clear_actions(self):
        """清空动作序列；clear_sequence 经录制回调通道自动刷新 UI"""
        self.engine.clear_sequence()

    def _on_list_selection_change(self, index: int):
        """选中项变化 -> 上移/下移按钮随边界启停；折叠行禁用移动"""
        rows = self.action_list.get_count()
        folded = self.action_list.is_folded_row(index)
        can_move = not folded
        self.action_list.move_up_button.config(
            state=tk.NORMAL if can_move and index > 0 else tk.DISABLED)
        self.action_list.move_down_button.config(
            state=tk.NORMAL if can_move and 0 <= index < rows - 1 else tk.DISABLED)
    
    # ==================== 引擎回调 ====================

    def _on_engine_event(self, event: EngineEvent):
        """引擎结构化状态事件（在工作线程中调用）"""
        self._dispatch_to_ui(lambda: self._apply_engine_event(event))

    def _apply_engine_event(self, event: EngineEvent):
        """按事件更新 UI 状态机（在主线程中执行，不做字符串解析）"""
        handlers = {
            EngineEvent.RECORDING_STARTED: (
                self.status_bar.set_recording,
                lambda: self.control_buttons.update_recording_state(True),
            ),
            EngineEvent.RECORDING_STOPPED: (
                self.status_bar.set_recording_stopped,
                lambda: self.control_buttons.update_recording_state(False),
            ),
            EngineEvent.CLICKING_STARTED: (
                self.status_bar.set_clicking,
                lambda: self.control_buttons.update_clicking_state(True),
            ),
            EngineEvent.CLICKING_STOPPED: (
                self.status_bar.set_stopped,
                lambda: self.control_buttons.update_clicking_state(False),
            ),
        }
        handler = handlers.get(event)
        if handler:
            handler[0]()
            handler[1]()

    def _on_engine_status_change(self, status: str):
        """引擎状态文案回调（在工作线程中调用），仅用于未归类文案的兜底展示"""
        self._dispatch_to_ui(lambda: self._update_status_ui(status))

    def _update_status_ui(self, status: str):
        """兜底状态展示（在主线程中执行）；按钮状态由 _apply_engine_event 驱动"""
        self.status_bar.set_status(status)
    
    def _on_engine_recording_update(self, actions: list):
        """引擎录制更新回调（在工作线程中调用）"""
        # 通过队列转投主线程，避免跨线程直接操作 Tk
        self._dispatch_to_ui(lambda: self._update_actions_list_ui(actions))
    
    def _update_actions_list_ui(self, actions: list):
        """更新动作列表 UI（在主线程中执行）"""
        self._current_actions = actions
        self.action_list.update_actions([action.to_dict() for action in actions])

        # 有动作时启用点击/保存/编辑；无动作全部禁用
        has_actions = len(actions) > 0
        self.control_buttons.enable_click_button(has_actions)
        self.control_buttons.enable_save_button(has_actions)
        self.action_list.enable_edit_buttons(has_actions)
    
    def on_close(self):
        """窗口关闭事件"""
        self._closing = True

        # 取消所有挂起的定时器，防止销毁后触发 Tcl 后台错误
        for after_id in list(self._pending_afters):
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self._pending_afters.clear()

        if self.hotkey_manager is not None:
            try:
                self.hotkey_manager.stop()
            except Exception:
                pass
            self.hotkey_manager = None

        self.engine.cleanup()

        # 在 Tcl 环境仍存活时主动回收 Tk 变量包装对象（StringVar 等）：
        # 若留到解释器退出阶段，跨线程清理会触发 Tcl_AsyncDelete 硬崩溃
        gc.collect()
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
