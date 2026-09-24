"""
自动点击器 Pro - 主 UI 模块
纯 UI 层，不包含业务逻辑
"""

import os
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
    PADDING_LARGE, PADDING_SMALL,
    PADDING_WINDOW, PADDING_SECTION,
    HOTKEY_START_STOP, HOTKEY_START_RECORDING,
    HOTKEY_STOP_RECORDING, HOTKEY_CANCEL,
    PICK_COORD_COUNTDOWN_S,
)
from config import macro_library
from config.settings_store import load_settings, save_settings
from config.validation import validate_macro_sequence
from core.engine import ClickerEngine, EngineEvent
from core.macros import ClickAction
from ui.components import SettingsPanel, ActionList, ControlButtons, StatusBar
from ui.components.hotkey_settings import HotkeySettings, HOTKEY_FIELDS
from ui.components.macro_library_panel import MacroLibraryPanel
from ui.components.tutorial_dialog import TutorialDialog, should_show_tutorial
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

# 设置面板可持久化的字段（与 settings_panel.variables 对应）
_PANEL_KEYS = ('interval_ms', 'record_interval', 'hold_duration',
               'repeat_count', 'repeat_interval',
               'start_delay_s', 'auto_stop_s')


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

        # 构造末显式同步滚动区域：必须在 update_idletasks 之后，
        # 否则 main_frame.winfo_reqheight() 还是初始 1，纵向滚动条不会出
        self.root.update_idletasks()
        self._sync_scroll_region()

        # 首次启动自动弹出新手教程（勾选"不再显示"后记忆；
        # ACPRO_NO_TUTORIAL=1 供测试环境禁用）
        if (os.environ.get('ACPRO_NO_TUTORIAL') != '1'
                and should_show_tutorial(load_settings())):
            self._schedule_after(400, self._show_tutorial)

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
        """创建用户界面

        布局：外层 = 可滚动内容画布（row0，随窗口伸缩） + 固定状态栏（row1）。
        窗口过小放不下全部内容时自动出现竖向滚动条（滚轮/拖动均可），
        内容放得下时动作列表区吃掉全部余量、滚动条隐藏。
        """
        # 外层框架
        outer = ttk.Frame(self.root)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        # 滚动画布 + 竖向滚动条（初始隐藏）
        self.canvas = tk.Canvas(outer, highlightthickness=0)
        self.canvas.configure(yscrollincrement=40)
        self.v_scrollbar = ttk.Scrollbar(outer, orient="vertical",
                                         command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.v_scrollbar.grid_remove()

        # 内容主框架（窗口四周留出呼吸边距；用 grid_propagate(False) + 显式
        # width 锁住宽度，避免子控件（最严重的是 action_list 的列表框 + 工具栏
        # 组合宽度 ~826）把容器撑出画布——之前 settings_panel 被拉到 794 宽，
        # 文本框全部溢出可视区。高度在 _sync_scroll_region 里手动算并显式
        # 写入，否则 grid_propagate(False) 会让 reqheight 永远是 1）
        main_frame = ttk.Frame(self.canvas,
                               padding=(PADDING_WINDOW, PADDING_WINDOW,
                                        PADDING_WINDOW, PADDING_SMALL),
                               width=APP_WIDTH,
                               height=APP_HEIGHT)
        main_frame.grid_propagate(False)
        self.main_frame = main_frame
        self._inner_window = self.canvas.create_window(
            (0, 0), window=main_frame, anchor="nw", tags=("inner",))
        # 配置网格权重（动作列表所在行才是可伸缩的主体区域）
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        main_frame.bind("<Configure>", self._on_inner_resize)

        # 标题 + 快捷键提示
        self._create_title(main_frame)

        # 设置面板
        self.settings_panel = SettingsPanel(main_frame)
        self.settings_panel.set_pick_handler(self._pick_coordinates)
        self.settings_panel.grid(row=2, column=0, sticky="ew",
                                 pady=(0, PADDING_SECTION))

        # 控制按钮
        self.control_buttons = ControlButtons(main_frame)
        self.control_buttons.grid(row=3, column=0, sticky="ew",
                                  pady=(0, PADDING_SECTION))

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
                                pady=(0, PADDING_SECTION))
        self.library_panel.combo.bind(
            '<<ComboboxSelected>>', self._on_library_selection_changed)
        self._refresh_macro_library()

        # 恢复上次会话的参数设置（OP 式"记住上次配置"）
        saved_panel = load_settings().get('panel')
        if isinstance(saved_panel, dict):
            restored = {key: saved_panel[key] for key in _PANEL_KEYS
                        if isinstance(saved_panel.get(key), int)}
            if restored:
                self.settings_panel.set_values(restored)
            # v2.7 新增：点击类型 / 位置模式 / 固定坐标
            click_type = saved_panel.get('click_type')
            if click_type in ('single', 'double', 'triple'):
                self.settings_panel.set_click_type(click_type)
            position_mode = saved_panel.get('position_mode')
            if position_mode in ('cursor', 'fixed'):
                self.settings_panel.set_position_mode(position_mode)
            fixed_x = saved_panel.get('fixed_x')
            fixed_y = saved_panel.get('fixed_y')
            if isinstance(fixed_x, int) and isinstance(fixed_y, int):
                self.settings_panel.set_fixed_xy(fixed_x, fixed_y)

        # 全局快捷键自定义区
        self.hotkey_settings = HotkeySettings(main_frame,
                                              on_apply=self._apply_hotkeys)
        self.hotkey_settings.set_values(self.hotkeys)
        self.hotkey_settings.grid(row=5, column=0, sticky="ew",
                                  pady=(0, PADDING_SECTION))

        # 动作列表（占据剩余空间）
        self.action_list = ActionList(main_frame)
        self.action_list.grid(row=6, column=0, sticky="nsew",
                              pady=(0, PADDING_SECTION))
        self.action_list.set_edit_callbacks(
            on_delete=self._on_delete_action,
            on_move_up=lambda: self._on_move_action(-1),
            on_move_down=lambda: self._on_move_action(1),
            on_clear=self._on_clear_actions,
            on_edit_coords=self._on_edit_coords,
        )
        self.action_list.on_selection_change = self._on_list_selection_change

        # 状态栏（固定在底部，不随内容滚动）
        self.status_bar = StatusBar(outer)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        # 滚轮：内容区任意控件上滚动均可滑动（列表框保留原生滚动）
        self._bind_mouse_wheel()

        # 滚动区域同步放在 __init__ 末尾（update_idletasks 之后）调用，
        # 此处 grid 还没排完，main_frame reqheight 还是 1，调了也没用

    # ==================== 滚动支持 ====================

    def _on_canvas_resize(self, event):
        """画布尺寸变化 -> 内框宽度跟随 + 重算滚动区域；
        同时把 main_frame 锁在画布宽度内，避免子控件把容器撑出可视区。
        纵向滚动条出现/消失会让 canvas 实际宽度变化，所以每次都重新钉一次。"""
        self.canvas.itemconfigure(self._inner_window, width=event.width)
        # 显式锁定 main_frame 宽度（grid_propagate(False) 防止子控件把它撑大）
        self.main_frame.configure(width=event.width)
        self._sync_scroll_region()

    def _on_inner_resize(self, _event=None):
        """内容尺寸变化 -> 重算滚动区域与滚动条显隐"""
        self._sync_scroll_region()

    def _calc_content_height(self) -> int:
        """累加所有 grid 子控件的底部 y 坐标得出实际所需高度。
        grid_propagate(False) 下 winfo_reqheight() 始终是构造时的初始高度，
        不能用作滚动判断依据——必须从子控件几何反推。"""
        max_bottom = 0
        for child in self.main_frame.winfo_children():
            info = child.grid_info()
            if not info:
                continue
            bottom = child.winfo_y() + child.winfo_height()
            if bottom > max_bottom:
                max_bottom = bottom
        # 加上下内边距
        pad = self.main_frame.cget("padding")
        if isinstance(pad, int):
            pad_bottom = pad
        elif len(pad) >= 4:
            pad_bottom = int(str(pad[3]))
        else:
            pad_bottom = 0
        return max_bottom + pad_bottom

    def _sync_scroll_region(self):
        """内容放不下 -> 显示滚动条；放得下 -> 内框填满画布（列表区吃余量）。
        grid_propagate(False) 下高度不会自动算，所以手动累加子控件底部 + 显式
        把 main_frame 的 height 写到需求值，scrollregion 才正确反映真实溢出。"""
        required = self._calc_content_height()
        visible = self.canvas.winfo_height()
        if visible <= 1:
            return  # 首次布局前画布尚无尺寸
        if required > visible:
            self.v_scrollbar.grid()
            self.canvas.configure(scrollregion=(0, 0, 0, required))
            self.canvas.itemconfigure(self._inner_window, height=required)
            self.main_frame.configure(height=required)
        else:
            self.v_scrollbar.grid_remove()
            self.canvas.configure(scrollregion=(0, 0, 0, visible))
            self.canvas.itemconfigure(self._inner_window, height=visible)
            self.main_frame.configure(height=visible)

    def _bind_mouse_wheel(self):
        """内容区任意控件上滚轮均滑动画布；列表框跳过（保留原生滚动）"""
        def on_wheel(event):
            step = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(step, "units")
            return "break"

        def bind_rec(widget):
            if isinstance(widget, tk.Listbox):
                return
            widget.bind("<MouseWheel>", on_wheel, add="+")
            for child in widget.winfo_children():
                bind_rec(child)

        bind_rec(self.main_frame)

    def _refresh_macro_library(self):
        """重新列举宏库（含元数据）并刷新下拉框"""
        items = {}
        for meta in macro_library.list_macros_with_meta():
            items[meta['name']] = macro_library.format_macro_display(meta)
        self.library_panel.refresh(items)
        self._update_library_detail()

    def _on_library_selection_changed(self, _event=None):
        """下拉选中变化 -> 更新元数据详情行"""
        self._update_library_detail()

    def _update_library_detail(self):
        name = self.library_panel.get_selected()
        if not name:
            self.library_panel.set_detail("")
            return
        meta = macro_library.get_macro_meta(name)
        parts = []
        actions = meta.get('actions')
        mtime = meta.get('mtime')
        parts.append(f"{actions} 个动作" if actions is not None else "无法读取内容")
        if mtime is not None:
            parts.append(f"保存于 {mtime:%Y-%m-%d %H:%M}")
        self.library_panel.set_detail(f"{name}：{' · '.join(parts)}")

    def _hotkey_hint_text(self) -> str:
        """根据当前生效的快捷键动态生成提示文案（紧凑版，避免标题区溢出）"""
        labels = dict(HOTKEY_FIELDS)
        parts = [f"{_display_key(self.hotkeys[action])} {labels[action]}"
                 for action, _ in HOTKEY_FIELDS]
        return " · ".join(parts)

    def _create_title(self, parent):
        """创建标题与快捷键提示（附新手教程入口）"""
        # 标题与提示都显式 sticky=nsew，配合 main_frame 列权重让它们真正居中
        # （默认 sticky 是空串，在 cell 比 widget 大时居中，但在某些 DPI/主题
        # 组合下会出现"偏右 50px"的诡异位移——显式指定最稳）
        title_label = ttk.Label(
            parent,
            text=f"{APP_NAME}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            foreground=COLOR_PRIMARY,
            anchor="center"
        )
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, PADDING_SMALL))

        hint_frame = ttk.Frame(parent)
        hint_frame.grid(row=1, column=0, sticky="ew", pady=(0, PADDING_LARGE))
        # 提示框内三段也统一 sticky，使整段始终居中
        self.hotkey_hint_label = ttk.Label(
            hint_frame,
            text=self._hotkey_hint_text(),
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground=COLOR_DISABLED,
            anchor="center"
        )
        self.hotkey_hint_label.grid(row=0, column=0)
        ttk.Label(hint_frame, text="  ·  ",
                  font=(FONT_FAMILY, FONT_SIZE_SMALL),
                  foreground=COLOR_DISABLED).grid(row=0, column=1)
        tutorial_link = ttk.Label(
            hint_frame, text="新手教程",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            foreground=COLOR_PRIMARY, cursor="hand2")
        tutorial_link.grid(row=0, column=2)
        tutorial_link.bind('<Button-1>', lambda _e: self._show_tutorial())

    # ==================== 新手教程 ====================

    def _show_tutorial(self):
        """打开新手教程对话框；勾选'不再显示'时记忆到 settings.json"""
        TutorialDialog(self.root, on_dont_show=self._mark_tutorial_seen)

    def _mark_tutorial_seen(self):
        """记录 tutorial_seen，之后启动不再自动弹出"""
        try:
            data = load_settings()
            data['tutorial_seen'] = True
            save_settings(data)
        except Exception:
            pass

    def _pick_coordinates(self):
        """拾取坐标：倒计时后抓取当前光标位置填入面板"""
        if self.engine.is_recording or self.engine.is_running:
            return

        def _tick(remaining: int):
            if remaining > 0:
                self.status_bar.set_status(
                    f"拾取坐标：{remaining} 秒内把鼠标移到目标位置...")
                self._schedule_after(1000, lambda: _tick(remaining - 1))
                return
            try:
                x, y = self.engine.mouse_controller.position
            except Exception:
                return
            x, y = int(x), int(y)
            self.settings_panel.set_fixed_xy(x, y)
            self.settings_panel.set_position_mode('fixed')
            self.status_bar.set_success(f"已拾取坐标 ({x}, {y})")

        _tick(PICK_COORD_COUNTDOWN_S)
    
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
        self.control_buttons.set_hotkey_labels(
            self.hotkeys['toggle'], self.hotkeys['start_recording'])

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
        """在主线程中消费 UI 任务队列；
        同时把 main_frame 高度跟上内容（grid_propagate(False) 下需手动算，
        而子控件 grid 完成时间不在 Configure 事件范围内，靠轮询兜底）"""
        while True:
            try:
                func = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except Exception as e:
                print(f"UI 任务执行失败：{e}")

        # 每轮都同步一次滚动区域（开销可忽略，比 ensure sync 漏触发靠谱）
        self._sync_scroll_region()

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
                # 内置连点模式：无需录制，按面板设置直接连点
                # （对标商业连点器：设好间隔 -> F8 -> 原地/定点连点）
                self._update_engine_config()
                if self.settings_panel.get_position_mode() == 'fixed':
                    xy = self.settings_panel.get_fixed_xy()
                    self.engine.set_fixed_position(xy)
                else:
                    self.engine.set_fixed_position(None)
                success = self.engine.start_simple_clicking()
                if success:
                    self.status_bar.set_clicking()
                return

            # 更新引擎配置
            self._update_engine_config()
            # 序列回放使用动作自带坐标，不套用内置连点的固定位置
            self.engine.set_fixed_position(None)

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
        """更新引擎配置并持久化面板数值（下次启动自动恢复）"""
        values = self.settings_panel.get_values()
        self.engine.update_config(
            interval_ms=values.get('interval_ms'),
            record_interval=values.get('record_interval'),
            hold_duration=values.get('hold_duration'),
            repeat_count=values.get('repeat_count'),
            repeat_interval=values.get('repeat_interval'),
            start_delay_s=values.get('start_delay_s'),
            auto_stop_s=values.get('auto_stop_s'),
            click_type=self.settings_panel.get_click_type()
        )
        self._save_panel_settings(values)

    def _save_panel_settings(self, values: dict):
        """把面板数值并入 settings.json（失败静默，不影响运行）"""
        try:
            data = load_settings()
            panel = {key: values[key] for key in _PANEL_KEYS
                     if key in values}
            # v2.7 新增字段的持久化
            panel['click_type'] = self.settings_panel.get_click_type()
            panel['position_mode'] = self.settings_panel.get_position_mode()
            fixed_xy = self.settings_panel.get_fixed_xy()
            if fixed_xy is not None:
                panel['fixed_x'], panel['fixed_y'] = fixed_xy
            data['panel'] = panel
            save_settings(data)
        except Exception:
            pass

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
        self._update_edit_coords_state()

    def _update_edit_coords_state(self):
        """坐标编辑仅对单个可选中的鼠标/移动类动作开放"""
        index = self.action_list.get_selected_index()
        rng = self.action_list.get_row_range(index)
        editable = False
        if rng is not None and rng[1] == rng[0]:
            action = self.engine.get_action(rng[0])
            editable = action is not None and action.kind in ('mouse', 'move')
        self.action_list.set_edit_coords_state(editable)

    def _show_coord_dialog(self, action: ClickAction) -> Optional[Tuple[int, int]]:
        """弹出坐标编辑对话框；取消/非法输入返回 None"""
        from ui.components.field_dialog import FieldDialog, int_field
        dlg = FieldDialog(
            self.root, "编辑坐标",
            [("X", action.x), ("Y", action.y)],
            validators=[int_field, int_field])
        self.root.wait_window(dlg)
        if dlg.result is None:
            return None
        try:
            return int(dlg.result["X"]), int(dlg.result["Y"])
        except (KeyError, ValueError):
            return None

    def _on_edit_coords(self):
        """弹出坐标微调对话框，写回选中动作的 x/y"""
        row_index = self.action_list.get_selected_index()
        rng = self.action_list.get_row_range(row_index)
        if rng is None or rng[1] != rng[0]:
            return
        seq_index = rng[0]
        action = self.engine.get_action(seq_index)
        if action is None:
            return

        coords = self._show_coord_dialog(action)
        if coords is None:
            return
        new_x, new_y = coords
        if self.engine.update_action_coordinates(seq_index, new_x, new_y):
            self._refresh_actions_ui(select=row_index)
            self.status_bar.set_success(f"已更新第 {seq_index + 1} 个动作的坐标")
    
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