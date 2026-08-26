"""
自动点击器引擎模块
处理所有核心业务逻辑：连点、录制、播放宏
与 UI 完全解耦，通过回调函数通信
"""

import enum
import threading
import time
from typing import List, Dict, Callable, Optional, Any, Tuple
from pynput import mouse, keyboard

from config.constants import (
    DEFAULT_INTERVAL_MS, DEFAULT_RECORD_INTERVAL,
    DEFAULT_HOLD_DURATION, DEFAULT_REPEAT_COUNT, DEFAULT_REPEAT_INTERVAL,
    DEFAULT_START_DELAY_S, DEFAULT_AUTO_STOP_S,
    HOTKEY_START_STOP, HOTKEY_START_RECORDING,
    HOTKEY_STOP_RECORDING, HOTKEY_CANCEL,
    STATUS_RECORDING,
    MOVE_MIN_DISTANCE_PX, MOVE_MIN_INTERVAL_MS,
    MULTI_CLICK_GAP_MS
)
from config.encryption import encrypt_macro, decrypt_macro
from config.validation import (
    validate_macro_sequence, is_modifier_name
)
from core.macros import ClickAction
from utils import win_windows
from utils.win_windows import WindowRect


class EngineEvent(enum.Enum):
    """引擎结构化状态事件（供 UI 状态机使用，避免解析中文字符串）"""
    CLICKING_STARTED = "clicking_started"
    CLICKING_STOPPED = "clicking_stopped"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"


class ClickerEngine:
    """自动点击器引擎 - 处理所有核心业务逻辑"""
    
    # 录制时需跳过的键名（全局快捷键），避免把控制键录进宏
    _SKIP_KEY_NAMES = frozenset(
        (HOTKEY_START_STOP, HOTKEY_START_RECORDING, HOTKEY_STOP_RECORDING, HOTKEY_CANCEL)
    )
    
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        # 运行状态 - 使用线程安全锁保护
        self._is_running = False
        self._is_recording = False
        self._lock = threading.Lock()
        
        # 录制相关
        self.click_sequence: List[ClickAction] = []
        self.recording_start_time = 0.0
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.Listener] = None
        # 录制期间按住未释放的修饰键（组合键追踪）：
        # [{'name': 'ctrl_l', 'used': False}]；used=True 表示已被某个组合键消费
        self._held_modifiers: List[Dict[str, Any]] = []
        # 拖拽轨迹采样：仅鼠标按键按下期间记录移动点
        self._mouse_down = False
        self._last_move_point: Optional[tuple] = None
        self._last_move_time = 0.0
        # 录制期间状态栏光标坐标的节流时间戳
        self._last_cursor_notify = 0.0

        # 配置参数
        self.interval_ms = DEFAULT_INTERVAL_MS
        self.record_interval = DEFAULT_RECORD_INTERVAL
        self.hold_duration = DEFAULT_HOLD_DURATION
        self.repeat_count = DEFAULT_REPEAT_COUNT
        self.repeat_interval = DEFAULT_REPEAT_INTERVAL
        self.start_delay_s = DEFAULT_START_DELAY_S   # 延迟启动（秒）
        self.auto_stop_s = DEFAULT_AUTO_STOP_S       # 自动停止（秒，0=不限时）

        # 内置连点模式（无序列直接开始时生效，对标商业连点器）
        self.click_type = 'single'                   # single / double / triple
        self.fixed_position: Optional[Tuple[int, int]] = None  # None=跟随光标

        # 回调函数
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_recording_update: Optional[Callable[[List[ClickAction]], None]] = None
        # 结构化状态事件（UI 状态机应优先使用它而非解析状态文案）
        self.on_engine_event: Optional[Callable[[EngineEvent], None]] = None
        
        # 录制过滤钩子：接收 (x, y)，返回 True 表示该点击不计入录制。
        # UI 层用它来排除用户点击本程序窗口（例如"停止录制"按钮）的动作。
        self.ignore_click_predicate: Optional[Callable[[int, int], bool]] = None

        # 录制时需跳过的键名（全局快捷键），避免把控制键录进宏。
        # 实例级副本：用户自定义快捷键时由 set_skip_key_names 更新。
        self._skip_key_names: set = set(self._SKIP_KEY_NAMES)

        # 窗口锚定：录制时取前台窗口信息、回放时按标题重定位窗口。
        # 可注入替换（测试/特殊环境），非 Windows 平台为返回 None 的空实现。
        self.foreground_provider = win_windows.get_foreground_window_info
        self.window_locater = win_windows.find_client_rect_by_title
        self._anchor_warned: set = set()

        # 录制通知节流：100ms 内只触发一次 UI 更新，避免高频录制时闪烁。
        self._recording_notify_throttle_ms: int = 100
        self._last_recording_notify_time: float = 0.0
    
    # ==================== 属性（线程安全） ====================
    
    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running
    
    @is_running.setter
    def is_running(self, value: bool):
        with self._lock:
            self._is_running = value
    
    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording
    
    @is_recording.setter
    def is_recording(self, value: bool):
        with self._lock:
            self._is_recording = value
    
    # ==================== 配置管理 ====================
    
    def update_config(self, interval_ms: Optional[int] = None, record_interval: Optional[int] = None,
                     hold_duration: Optional[int] = None, repeat_count: Optional[int] = None,
                     repeat_interval: Optional[int] = None,
                     start_delay_s: Optional[float] = None,
                     auto_stop_s: Optional[float] = None,
                     click_type: Optional[str] = None):
        """更新配置参数"""
        with self._lock:
            if interval_ms is not None:
                self.interval_ms = interval_ms
            if record_interval is not None:
                self.record_interval = record_interval
            if hold_duration is not None:
                self.hold_duration = hold_duration
            if repeat_count is not None:
                self.repeat_count = repeat_count
            if repeat_interval is not None:
                self.repeat_interval = repeat_interval
            if start_delay_s is not None:
                self.start_delay_s = start_delay_s
            if auto_stop_s is not None:
                self.auto_stop_s = auto_stop_s
            if click_type in ('single', 'double', 'triple'):
                self.click_type = click_type

    def set_fixed_position(self, xy: Optional[Tuple[int, int]]):
        """设置内置连点模式的固定坐标；None 表示跟随光标"""
        with self._lock:
            self.fixed_position = xy

    # ==================== 回调设置 ====================

    def set_callbacks(self, on_status_change: Optional[Callable[[str], None]] = None,
                      on_recording_update: Optional[Callable[[List[ClickAction]], None]] = None,
                      recording_notify_throttle_ms: Optional[int] = None,
                      on_engine_event: Optional[Callable[[EngineEvent], None]] = None):
        """设置回调函数"""
        if on_status_change is not None:
            self.on_status_change = on_status_change
        if on_recording_update is not None:
            self.on_recording_update = on_recording_update
        if recording_notify_throttle_ms is not None:
            self._recording_notify_throttle_ms = recording_notify_throttle_ms
        if on_engine_event is not None:
            self.on_engine_event = on_engine_event

    def _emit_event(self, event: EngineEvent):
        """发出结构化状态事件（若已注册回调）"""
        if self.on_engine_event:
            try:
                self.on_engine_event(event)
            except Exception as e:
                print(f"状态事件回调执行失败：{e}")

    # ==================== 自动点击逻辑 ====================
    
    def start_clicking(self) -> bool:
        """开始自动点击"""
        if self.is_running:
            return False

        self.is_running = True

        self._emit_event(EngineEvent.CLICKING_STARTED)
        if self.on_status_change:
            self.on_status_change("正在点击...")

        # 在新线程中执行点击
        click_thread = threading.Thread(target=self._execute_clicking)
        click_thread.daemon = True
        click_thread.start()

        return True

    def stop_clicking(self):
        """停止自动点击"""
        self.is_running = False

        self._emit_event(EngineEvent.CLICKING_STOPPED)
        if self.on_status_change:
            self.on_status_change("已停止")
    
    def _wait_start_delay(self) -> bool:
        """延迟启动等待；等待期间保持对停止指令的响应。

        Returns:
            True = 正常到点；False = 等待期间被停止
        """
        delay = self.start_delay_s
        if delay <= 0:
            return True
        if self.on_status_change:
            self.on_status_change(f"{delay} 秒后开始...")
        end = time.perf_counter() + delay
        while self.is_running:
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return True
            time.sleep(min(0.1, remaining))
        return False

    def start_simple_clicking(self) -> bool:
        """开始内置连点（无需录制序列，对标商业连点器的核心用法）

        按 click_type（单击/双击/三击）在 fixed_position（固定位置）
        或当前光标处连续点击；repeat_count 为点击事件总数，<=0 表示无限。
        """
        if self.is_running:
            return False

        self.is_running = True

        self._emit_event(EngineEvent.CLICKING_STARTED)
        if self.on_status_change:
            self.on_status_change("正在点击...")

        click_thread = threading.Thread(target=self._execute_simple_clicking)
        click_thread.daemon = True
        click_thread.start()

        return True

    def _execute_simple_clicking(self):
        """内置连点主循环（在工作线程中运行）"""
        clicks_per_event = {'single': 1, 'double': 2, 'triple': 3}.get(
            self.click_type, 1)
        gap_s = MULTI_CLICK_GAP_MS / 1000.0
        try:
            if not self._wait_start_delay():
                return

            stop_deadline: Optional[float] = None
            if self.auto_stop_s > 0:
                stop_deadline = time.perf_counter() + self.auto_stop_s

            btn = mouse.Button.left
            events_done = 0
            infinite = self.repeat_count <= 0
            while self.is_running:
                if not infinite and events_done >= self.repeat_count:
                    break
                if (stop_deadline is not None
                        and time.perf_counter() >= stop_deadline):
                    break

                for i in range(clicks_per_event):
                    if not self.is_running:
                        break
                    if (stop_deadline is not None
                            and time.perf_counter() >= stop_deadline):
                        break
                    target = self.fixed_position
                    if target is not None:
                        self.mouse_controller.position = target
                    self.mouse_controller.press(btn)
                    self.mouse_controller.release(btn)
                    if i < clicks_per_event - 1:
                        time.sleep(gap_s)

                events_done += 1
                # 还有下一轮（或无限模式）时等待点击间隔
                more = infinite or events_done < self.repeat_count
                if more and self.is_running:
                    time.sleep(max(self.interval_ms, 1) / 1000.0)

        except Exception as e:
            print(f"连点执行错误：{e}")

        finally:
            self.stop_clicking()

    def _execute_clicking(self):
        """执行点击操作的核心方法（在工作线程中运行）

        时序策略：
        - 序列中存在非零时间戳（录制产生）→ 按时间戳原速回放，每轮重复重新对齐；
        - 全零时间戳（旧文件/手工构造）→ 退回固定 interval_ms 间隔回放。
        auto_stop_s > 0 时整个运行限时，到点即停。
        """
        try:
            if not self._wait_start_delay():
                return

            stop_deadline: Optional[float] = None
            if self.auto_stop_s > 0:
                stop_deadline = time.perf_counter() + self.auto_stop_s

            sequence = list(self.click_sequence)
            paired = self._pair_press_releases(sequence)
            use_timestamps = any(a.timestamp > 0 for a in sequence)
            self._anchor_warned = set()

            # repeat_count<=0 表示无限循环，直到手动停止或达到自动停止时限
            rep = 0
            while self.is_running:
                if self.repeat_count > 0 and rep >= self.repeat_count:
                    break
                if (stop_deadline is not None
                        and time.perf_counter() >= stop_deadline):
                    break

                start = time.perf_counter()
                for index, action in enumerate(sequence):
                    if not self.is_running:
                        break
                    if (stop_deadline is not None
                            and time.perf_counter() >= stop_deadline):
                        break
                    if use_timestamps:
                        # 对齐到录制时刻；已落后则立即执行，避免误差累积
                        delay = action.timestamp - (time.perf_counter() - start)
                        if delay > 0:
                            time.sleep(delay)
                    elif len(sequence) > 1 and index > 0:
                        time.sleep(self.interval_ms / 1000.0)

                    if not self.is_running:
                        break
                    self._perform_action(action, paired.get(index))

                # 还有下一轮（或无限模式）时等待重复间隔
                rep += 1
                more_rounds = self.repeat_count <= 0 or rep < self.repeat_count
                if more_rounds and self.is_running:
                    time.sleep(self.repeat_interval / 1000.0)

        except Exception as e:
            print(f"点击执行错误：{e}")

        finally:
            self.stop_clicking()

    @staticmethod
    def _pair_press_releases(sequence: List[ClickAction]) -> Dict[int, int]:
        """把 press 与其后匹配的 release 配对。

        返回 {press下标: release下标}。配对的 press 不注入 hold_duration
        自动释放——由时间轴上的真实 release 负责抬起（拖拽因此得以还原）。
        未配对的孤立 press（无对应释放）按"轻点+hold_duration"语义处理。
        匹配键为 (kind, button/key)，忽略坐标差异（拖拽起止坐标不同属正常）。
        """
        open_stacks: Dict[Tuple[str, str], List[int]] = {}
        pairs: Dict[int, int] = {}
        for i, action in enumerate(sequence):
            target = (action.kind,
                      action.key if action.kind == 'key' else action.button,
                      )
            key_tuple: Tuple[str, str] = (target[0], target[1] or '')
            if action.action_type == 'press':
                open_stacks.setdefault(key_tuple, []).append(i)
            elif action.action_type == 'release':
                stack = open_stacks.get(key_tuple)
                if stack:
                    pairs[stack.pop()] = i
        return pairs
    
    @staticmethod
    def _key_to_name(key) -> Optional[str]:
        """把 pynput 键对象转成规范键名字符串。
        
        普通字符键（如 'a'、'1'、空格）返回其字符；特殊键（如 Enter、F1、
        左 Ctrl）返回其枚举名（'enter'、'f1'、'ctrl_l'）。无法识别返回 None。
        """
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        name = getattr(key, 'name', None)
        return name if name else None
    
    def _perform_action(self, action, paired_release_index: Optional[int]):
        """执行单个动作（回放主入口）

        - kind='move'：仅移动鼠标到解析后的坐标（拖拽轨迹点，无按键）；
        - kind='chord'：修饰键按录制顺序按下 -> 轻点触发键 -> 修饰键逆序释放；
        - kind='key'：配对的 press 只按下（release 由时间轴负责），
          孤立 press 按"轻点"语义（hold_duration>0 时按住指定时长）；
        - kind='mouse'：带 modifiers 时先对称按下/释放修饰键；
          配对 press 不自动抬起（还原拖拽），孤立 press 注入 hold_duration。
        """
        if action.kind == 'move':
            x, y = self._resolve_anchor(action)
            self.mouse_controller.position = (x, y)
        elif action.kind == 'chord':
            self._perform_chord_action(action)
        elif action.kind == 'key':
            self._perform_key_action(action, paired_release_index is not None)
        else:
            self._perform_mouse_action(action, paired_release_index is not None)

    def _press_modifiers(self, modifiers: List[str]):
        """按录制顺序按下修饰键"""
        for name in modifiers:
            k = self._resolve_key(name)
            if k is not None:
                self.keyboard_controller.press(k)

    def _release_modifiers(self, modifiers: List[str]):
        """按录制的逆序释放修饰键"""
        for name in reversed(modifiers):
            k = self._resolve_key(name)
            if k is not None:
                self.keyboard_controller.release(k)

    def _resolve_key(self, name: Optional[str]):
        """把规范键名解析回 pynput 键对象；无法解析返回 None。"""
        if not name:
            return None
        if len(name) == 1:
            # 单字符 -> KeyCode（'a'、' '、'1' 等）
            return keyboard.KeyCode(char=name)
        # 特殊键名 -> keyboard.Key 枚举成员（'enter'、'f1'、'ctrl_l' 等）
        return getattr(keyboard.Key, name, None)

    def _perform_chord_action(self, action):
        """执行键盘组合键：Ctrl+C -> 按住 ctrl_l，轻点 c，松开 ctrl_l"""
        trigger = self._resolve_key(action.key)
        if trigger is None:
            return

        self._press_modifiers(action.modifiers)
        try:
            self.keyboard_controller.press(trigger)
            if self.hold_duration > 0:
                time.sleep(self.hold_duration / 1000.0)
            self.keyboard_controller.release(trigger)
        finally:
            self._release_modifiers(action.modifiers)

    def _resolve_anchor(self, action) -> Tuple[int, int]:
        """把鼠标动作解析为屏幕绝对坐标。

        带窗口锚定时按同名窗口当前位置重算；找不到窗口则降级为
        绝对坐标执行，并对每个标题只发一次状态栏警告。
        """
        if (action.anchor_title
                and action.win_rel_x is not None
                and action.win_rel_y is not None):
            rect: Optional[WindowRect] = None
            locater = self.window_locater
            if locater is not None:
                try:
                    rect = locater(action.anchor_title)
                except Exception:
                    rect = None
            if rect is not None:
                return (rect.left + action.win_rel_x,
                        rect.top + action.win_rel_y)
            if action.anchor_title not in self._anchor_warned:
                self._anchor_warned.add(action.anchor_title)
                if self.on_status_change:
                    self.on_status_change(
                        f"未找到窗口“{action.anchor_title}”，"
                        "相关动作已按绝对坐标执行")
        return action.x, action.y

    def _perform_mouse_action(self, action, paired: bool):
        """执行单个鼠标事件。paired=True 表示序列中存在其对应的 release。"""
        mods = action.modifiers or []
        button_map = {
            'left': mouse.Button.left,
            'right': mouse.Button.right,
            'middle': mouse.Button.middle,
            'x1': mouse.Button.x1,
            'x2': mouse.Button.x2
        }
        btn = button_map.get(action.button, mouse.Button.left)

        if action.action_type == 'press':
            self._press_modifiers(mods)
            try:
                x, y = self._resolve_anchor(action)
                self.mouse_controller.position = (x, y)
                self.mouse_controller.press(btn)
                if paired:
                    # 拖拽/按住场景：保持按下状态，等待时间轴上的 release
                    return
                if self.hold_duration > 0:
                    time.sleep(self.hold_duration / 1000.0)
                self.mouse_controller.release(btn)
            finally:
                if not paired:
                    self._release_modifiers(mods)
        elif action.action_type == 'release':
            x, y = self._resolve_anchor(action)
            self.mouse_controller.position = (x, y)
            self.mouse_controller.release(btn)
            if mods:
                self._release_modifiers(mods)

    def _perform_key_action(self, action, paired: bool):
        """执行单键事件。paired=True 表示存在后续 release；否则轻点。"""
        k = self._resolve_key(action.key)
        if k is None:
            return

        if action.action_type in ('press', 'tap'):
            self.keyboard_controller.press(k)
            if paired:
                return  # 等待时间轴上的 release 动作
            if self.hold_duration > 0:
                time.sleep(self.hold_duration / 1000.0)
            self.keyboard_controller.release(k)
        elif action.action_type == 'release':
            self.keyboard_controller.release(k)
    
    # ==================== 宏录制逻辑 ====================

    def start_recording(self) -> bool:
        """开始录制点击序列"""
        if self.is_recording:
            return False

        self.is_recording = True
        self.click_sequence = []
        self._held_modifiers = []
        self._mouse_down = False
        self._last_move_point = None
        self.recording_start_time = time.time()

        self._emit_event(EngineEvent.RECORDING_STARTED)
        if self.on_status_change:
            self.on_status_change(STATUS_RECORDING)

        # 开始监听鼠标和键盘事件
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        return True

    def stop_recording(self):
        """停止录制（可从监听线程与主线程并发调用，幂等）"""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            # 先在锁内摘除引用：并发调用方拿到的是 None，直接返回
            mouse_listener = self.mouse_listener
            keyboard_listener = self.keyboard_listener
            self.mouse_listener = None
            self.keyboard_listener = None

        # 停止监听（stop 本身线程安全，放到锁外避免长时间持锁）
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()

        # 丢弃仍按住的修饰键（不补录），避免半截组合键入宏
        self._held_modifiers = []
        self._mouse_down = False
        self._last_move_point = None

        self._emit_event(EngineEvent.RECORDING_STOPPED)
        if self.on_status_change:
            self.on_status_change("录制已停止")

    def _append_action(self, action: ClickAction):
        """线程安全地追加动作并节流通知 UI"""
        with self._lock:
            self.click_sequence.append(action)
        self._maybe_notify_recording()

    def _current_modifiers(self) -> List[str]:
        """当前按住的修饰键名列表（按下顺序）"""
        return [entry['name'] for entry in self._held_modifiers]

    def _mark_modifiers_used(self):
        """把当前按住的所有修饰键标记为已消费（参与过组合键/组合点击）"""
        for entry in self._held_modifiers:
            entry['used'] = True

    def _capture_anchor(self, x: int, y: int) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """捕获 (x,y) 所在前台窗口的锚定信息；取不到返回 (None, None, None)"""
        provider = self.foreground_provider
        if provider is None:
            return None, None, None
        try:
            info: Optional[WindowRect] = provider()
        except Exception:
            info = None
        if (info is not None
                and info.left <= x < info.right
                and info.top <= y < info.bottom):
            return info.title, x - info.left, y - info.top
        return None, None, None

    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击回调"""
        if not self.is_recording:
            return

        # 过滤掉落在本程序窗口内的点击（如点"停止录制"按钮），
        # 否则这些操作 UI 的动作会被误录进宏里。
        if self.ignore_click_predicate is not None:
            try:
                if self.ignore_click_predicate(x, y):
                    return
            except Exception:
                pass  # 过滤器异常不应中断录制

        # 确定按钮名称
        button_name = 'left'
        if button == mouse.Button.right:
            button_name = 'right'
        elif button == mouse.Button.middle:
            button_name = 'middle'
        elif button == mouse.Button.x1:
            button_name = 'x1'
        elif button == mouse.Button.x2:
            button_name = 'x2'

        action_type = 'press' if pressed else 'release'

        # 拖拽轨迹只在"有按键按住"期间采样；
        # 按下时以点击点为初始基线，让抖动过滤从落点即刻生效
        self._mouse_down = pressed
        if pressed:
            self._last_move_point = (x, y)
            self._last_move_time = time.time()

        # 组合键点击（如 Shift+单击）：修饰键记录在 press 与 release 两侧，
        # 回放侧负责对称按下/释放；这些修饰键视为已消费。
        mods: List[str] = []
        if action_type == 'press' and self._held_modifiers:
            mods = self._current_modifiers()
            self._mark_modifiers_used()
        elif action_type == 'release':
            mods = self._current_modifiers()
            self._mark_modifiers_used()

        # 窗口锚定：点击落在前台窗口客户区内时，记录标题与相对偏移
        anchor_title, rel_x, rel_y = self._capture_anchor(x, y)

        timestamp = time.time() - self.recording_start_time
        click_action = ClickAction(x, y, button_name, action_type, timestamp,
                                   modifiers=mods,
                                   anchor_title=anchor_title,
                                   win_rel_x=rel_x,
                                   win_rel_y=rel_y)
        self._append_action(click_action)

    def _on_mouse_move(self, x, y):
        """鼠标移动回调：节流播报光标位置；拖拽期间按双阈值采样轨迹"""
        now = time.time()

        # 录制期间（无论是否按住）节流显示光标位置，给用户落点反馈
        if self.is_recording and self.on_status_change:
            if now - self._last_cursor_notify >= 0.25:
                self._last_cursor_notify = now
                try:
                    self.on_status_change(f"正在录制… 光标 ({x}, {y})")
                except Exception:
                    pass

        if not self.is_recording or not self._mouse_down:
            return

        now = time.time()
        if self._last_move_point is not None:
            last_x, last_y = self._last_move_point
            dist_sq = (x - last_x) ** 2 + (y - last_y) ** 2
            if dist_sq < MOVE_MIN_DISTANCE_PX ** 2:
                return
            elapsed_ms = (now - self._last_move_time) * 1000.0
            if elapsed_ms < MOVE_MIN_INTERVAL_MS:
                return

        self._last_move_point = (x, y)
        self._last_move_time = now

        anchor_title, rel_x, rel_y = self._capture_anchor(x, y)
        timestamp = now - self.recording_start_time
        move_action = ClickAction(x, y, '', 'move', timestamp,
                                  kind='move',
                                  anchor_title=anchor_title,
                                  win_rel_x=rel_x,
                                  win_rel_y=rel_y)
        self._append_action(move_action)

    def _maybe_notify_recording(self):
        """节流录制通知（100ms 内最多触发一次）"""
        now = time.time()
        if now - self._last_recording_notify_time < self._recording_notify_throttle_ms / 1000.0:
            return
        self._last_recording_notify_time = now
        if self.on_recording_update:
            with self._lock:
                snapshot = list(self.click_sequence)
            self.on_recording_update(snapshot)

    def _on_key_press(self, key):
        """键盘按下回调 - ESC 停止录制；普通键录轻点；组合键录单条 chord"""
        if not self.is_recording:
            return

        # ESC 停止录制
        if key == keyboard.Key.esc:
            self.stop_recording()
            return

        # 把按键转成规范键名；无法识别的键忽略
        name = self._key_to_name(key)
        if name is None:
            return

        # 跳过全局快捷键键（F8/F10/F11/ESC 或自定义），避免把控制键录进宏
        if name in self._skip_key_names:
            return

        timestamp = time.time() - self.recording_start_time

        # 修饰键：先挂起不立即入列——它可能属于尚未发生的组合键
        if is_modifier_name(name):
            self._held_modifiers.append({'name': name, 'used': False})
            return

        # 非修饰键 + 有修饰键按住 -> 录为一条 chord（如 Ctrl+C）
        if self._held_modifiers:
            self._mark_modifiers_used()
            action = ClickAction(0, 0, '', 'press', timestamp,
                                 kind='chord', key=name,
                                 modifiers=self._current_modifiers())
        else:
            # 普通单键：录为轻点语义的 key 动作
            action = ClickAction(0, 0, '', 'press', timestamp,
                                 kind='key', key=name)

        self._append_action(action)

    def _on_key_release(self, key):
        """键盘释放回调 - 未被任何组合键消费的修饰键在此补录为单键轻点"""
        if not self.is_recording:
            return

        name = self._key_to_name(key)
        if name is None or not is_modifier_name(name):
            return

        # 从按住列表中移除最后一次匹配的该修饰键
        for index in range(len(self._held_modifiers) - 1, -1, -1):
            entry = self._held_modifiers[index]
            if entry['name'] == name:
                self._held_modifiers.pop(index)
                if not entry['used']:
                    # 孤立的修饰键点按（如单独敲一下 Shift）也录入宏
                    timestamp = time.time() - self.recording_start_time
                    action = ClickAction(0, 0, '', 'press', timestamp,
                                         kind='key', key=name)
                    self._append_action(action)
                return
    
    def set_skip_key_names(self, names) -> None:
        """更新录制时应跳过的快捷键键名集合（线程安全）"""
        with self._lock:
            self._skip_key_names = {str(n).lower() for n in names}

    def get_skip_key_names(self) -> set:
        """当前录制跳过键名集合（只读副本）"""
        with self._lock:
            return set(self._skip_key_names)

    # ==================== 序列编辑 ====================

    def get_sequence(self) -> List[ClickAction]:
        """获取动作序列的只读副本（线程安全）"""
        with self._lock:
            return list(self.click_sequence)

    def remove_action(self, index: int) -> bool:
        """删除指定下标的动作；越界返回 False"""
        with self._lock:
            if 0 <= index < len(self.click_sequence):
                del self.click_sequence[index]
                return True
        return False

    def remove_range(self, start: int, end: int) -> int:
        """删除闭区间 [start, end] 内的动作，返回实际删除数量"""
        with self._lock:
            n = len(self.click_sequence)
            if not (0 <= start <= end < n):
                return 0
            del self.click_sequence[start:end + 1]
            return end - start + 1

    def update_action_coordinates(self, index: int, x: int, y: int) -> bool:
        """更新指定动作的坐标（仅鼠标/移动类动作有意义）；越界返回 False"""
        with self._lock:
            if 0 <= index < len(self.click_sequence):
                self.click_sequence[index].x = int(x)
                self.click_sequence[index].y = int(y)
                return True
        return False

    def get_action(self, index: int) -> Optional[ClickAction]:
        """获取指定下标动作的只读副本；越界返回 None"""
        with self._lock:
            if 0 <= index < len(self.click_sequence):
                action = self.click_sequence[index]
                return ClickAction.from_dict(action.to_dict())
        return None

    def move_action(self, src: int, dst: int) -> bool:
        """把 src 下标的动作移动到 dst 下标（其余元素顺移）；越界返回 False"""
        with self._lock:
            n = len(self.click_sequence)
            if not (0 <= src < n and 0 <= dst < n) or src == dst:
                return False
            action = self.click_sequence.pop(src)
            self.click_sequence.insert(dst, action)
            return True

    def clear_sequence(self):
        """清空动作序列并通知 UI"""
        with self._lock:
            self.click_sequence = []
        if self.on_recording_update:
            try:
                self.on_recording_update([])
            except Exception as e:
                print(f"清空回调执行失败：{e}")

    # ==================== 宏文件操作 ====================
    
    def save_sequence(self, filepath: str):
        """保存点击序列到加密文件"""
        # 验证序列
        actions_data = [action.to_dict() for action in self.click_sequence]
        is_valid, error_msg = validate_macro_sequence(actions_data)
        
        if not is_valid:
            raise ValueError(f"宏序列验证失败：{error_msg}")
        
        # 加密保存
        encrypt_macro(actions_data, filepath)
    
    def load_sequence(self, filepath: str):
        """从加密文件加载点击序列"""
        # 解密加载
        actions_data = decrypt_macro(filepath)
        
        # 验证序列
        is_valid, error_msg = validate_macro_sequence(actions_data)
        if not is_valid:
            raise ValueError(f"宏序列验证失败：{error_msg}")
        
        # 转换为 ClickAction 对象
        self.click_sequence = [ClickAction.from_dict(data) for data in actions_data]
        
        # 通知 UI 更新
        if self.on_recording_update:
            self.on_recording_update(self.click_sequence.copy())
    
    # ==================== 资源清理 ====================
    
    def cleanup(self):
        """清理资源"""
        self.stop_clicking()
        self.stop_recording()
