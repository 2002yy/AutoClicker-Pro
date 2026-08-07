"""
自动点击器引擎模块
处理所有核心业务逻辑：连点、录制、播放宏
与 UI 完全解耦，通过回调函数通信
"""

import threading
import time
from typing import List, Dict, Callable, Optional, Any
from pynput import mouse, keyboard

from config.constants import (
    DEFAULT_INTERVAL_MS, DEFAULT_RECORD_INTERVAL, 
    DEFAULT_HOLD_DURATION, DEFAULT_REPEAT_COUNT, DEFAULT_REPEAT_INTERVAL,
    HOTKEY_START_STOP, HOTKEY_START_RECORDING,
    HOTKEY_STOP_RECORDING, HOTKEY_CANCEL,
    STATUS_RECORDING
)
from config.encryption import encrypt_macro, decrypt_macro
from config.validation import validate_time_inputs, validate_macro_sequence
from core.macros import ClickAction


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
        
        # 配置参数
        self.interval_ms = DEFAULT_INTERVAL_MS
        self.record_interval = DEFAULT_RECORD_INTERVAL
        self.hold_duration = DEFAULT_HOLD_DURATION
        self.repeat_count = DEFAULT_REPEAT_COUNT
        self.repeat_interval = DEFAULT_REPEAT_INTERVAL
        
        # 回调函数
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_recording_update: Optional[Callable[[List[ClickAction]], None]] = None
        
        # 录制过滤钩子：接收 (x, y)，返回 True 表示该点击不计入录制。
        # UI 层用它来排除用户点击本程序窗口（例如"停止录制"按钮）的动作。
        self.ignore_click_predicate: Optional[Callable[[int, int], bool]] = None

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
    
    def update_config(self, interval_ms: int = None, record_interval: int = None,
                     hold_duration: int = None, repeat_count: int = None, 
                     repeat_interval: int = None):
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
    
    # ==================== 回调设置 ====================

    def set_callbacks(self, on_status_change: Callable[[str], None] = None,
                      on_recording_update: Callable[[List[ClickAction]], None] = None,
                      recording_notify_throttle_ms: int = None):
        """设置回调函数"""
        if on_status_change is not None:
            self.on_status_change = on_status_change
        if on_recording_update is not None:
            self.on_recording_update = on_recording_update
        if recording_notify_throttle_ms is not None:
            self._recording_notify_throttle_ms = recording_notify_throttle_ms

    # ==================== 自动点击逻辑 ====================
    
    def start_clicking(self) -> bool:
        """开始自动点击"""
        if self.is_running:
            return False
        
        self.is_running = True
        
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
        
        if self.on_status_change:
            self.on_status_change("已停止")
    
    def _execute_clicking(self):
        """执行点击操作的核心方法（在工作线程中运行）"""
        try:
            for i in range(self.repeat_count):
                if not self.is_running:
                    break
                
                for click_action in self.click_sequence:
                    if not self.is_running:
                        break
                    
                    if click_action.kind == 'key':
                        self._perform_key_action(click_action)
                    else:
                        self._perform_mouse_action(click_action)
                    
                    # 根据间隔等待
                    if len(self.click_sequence) > 1:
                        time.sleep(self.interval_ms / 1000.0)
                
                # 如果不是最后一次重复，则等待重复间隔
                if i < self.repeat_count - 1 and self.is_running:
                    time.sleep(self.repeat_interval / 1000.0)
        
        except Exception as e:
            print(f"点击执行错误：{e}")
        
        finally:
            self.stop_clicking()
    
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
    
    def _resolve_key(self, name: Optional[str]):
        """把规范键名解析回 pynput 键对象；无法解析返回 None。"""
        if not name:
            return None
        if len(name) == 1:
            # 单字符 -> KeyCode（'a'、' '、'1' 等）
            return keyboard.KeyCode(char=name)
        # 特殊键名 -> keyboard.Key 枚举成员（'enter'、'f1'、'ctrl_l' 等）
        return getattr(keyboard.Key, name, None)
    
    def _perform_mouse_action(self, action):
        """执行单个鼠标点击动作"""
        self.mouse_controller.position = (action.x, action.y)
        
        button_map = {
            'left': mouse.Button.left,
            'right': mouse.Button.right,
            'middle': mouse.Button.middle,
            'x1': mouse.Button.x1,
            'x2': mouse.Button.x2
        }
        btn = button_map.get(action.button, mouse.Button.left)
        
        if action.action_type == 'press':
            self.mouse_controller.press(btn)
            if self.hold_duration > 0:
                time.sleep(self.hold_duration / 1000.0)
                self.mouse_controller.release(btn)
        elif action.action_type == 'release':
            self.mouse_controller.release(btn)
    
    def _perform_key_action(self, action):
        """执行单个键盘动作。
        
        录制时只记录 'press'，因此回放时对 press 采用"轻点"语义：
        按下后若 hold_duration<=0 立即释放（避免按键卡住），否则按住指定时长再释放。
        """
        k = self._resolve_key(action.key)
        if k is None:
            return
        
        if action.action_type in ('press', 'tap'):
            self.keyboard_controller.press(k)
            if self.hold_duration > 0:
                time.sleep(self.hold_duration / 1000.0)
                self.keyboard_controller.release(k)
            else:
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
        self.recording_start_time = time.time()
        
        if self.on_status_change:
            self.on_status_change(STATUS_RECORDING)
        
        # 开始监听鼠标和键盘事件
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        return True
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # 停止监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        if self.on_status_change:
            self.on_status_change("录制已停止")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动回调"""
        pass  # 暂时不需要处理移动事件
    
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
        
        # 创建点击动作
        action_type = 'press' if pressed else 'release'
        timestamp = time.time() - self.recording_start_time
        
        click_action = ClickAction(x, y, button_name, action_type, timestamp)
        
        with self._lock:
            self.click_sequence.append(click_action)

        # 节流通知 UI：100ms 内只触发一次，避免高频录制闪烁
        self._maybe_notify_recording()

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
        """键盘按键回调 - ESC 停止录制，其余按键作为键盘动作录制"""
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
        
        # 跳过全局快捷键键（F8/F10/F11/ESC），避免把控制键录进宏
        if name in self._SKIP_KEY_NAMES:
            return
        
        # 记录为键盘动作（录制只记录按下，回放时按轻点语义执行）
        timestamp = time.time() - self.recording_start_time
        action = ClickAction(0, 0, '', 'press', timestamp, kind='key', key=name)
        
        with self._lock:
            self.click_sequence.append(action)

        # 节流通知 UI
        self._maybe_notify_recording()
    
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
