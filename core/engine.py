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
    KEY_MAP
)
from config.encryption import encrypt_macro, decrypt_macro
from config.validation import validate_time_inputs, validate_macro_sequence


class ClickAction:
    """表示一个点击动作"""
    
    def __init__(self, x: int, y: int, button: str, action_type: str, timestamp: float = 0):
        self.x = x
        self.y = y
        self.button = button  # 'left', 'right', 'middle'
        self.action_type = action_type  # 'press' 或 'release'
        self.timestamp = timestamp  # 相对于序列开始的时间戳
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'button': self.button,
            'action_type': self.action_type,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClickAction':
        """从字典创建"""
        return cls(
            x=data['x'],
            y=data['y'],
            button=data['button'],
            action_type=data['action_type'],
            timestamp=data.get('timestamp', 0)
        )


class ClickerEngine:
    """自动点击器引擎 - 处理所有核心业务逻辑"""
    
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
                    
                    # 移动鼠标到指定位置
                    self.mouse_controller.position = (click_action.x, click_action.y)
                    
                    # 获取按钮对象
                    button_map = {
                        'left': mouse.Button.left,
                        'right': mouse.Button.right,
                        'middle': mouse.Button.middle,
                        'x1': mouse.Button.x1,
                        'x2': mouse.Button.x2
                    }
                    btn = button_map.get(click_action.button, mouse.Button.left)
                    
                    # 执行点击动作
                    if click_action.action_type == 'press':
                        self.mouse_controller.press(btn)
                        
                        # 如果需要按住一段时间
                        if self.hold_duration > 0:
                            time.sleep(self.hold_duration / 1000.0)
                            self.mouse_controller.release(btn)
                    
                    elif click_action.action_type == 'release':
                        self.mouse_controller.release(btn)
                    
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
    
    # ==================== 宏录制逻辑 ====================
    
    def start_recording(self) -> bool:
        """开始录制点击序列"""
        if self.is_recording:
            return False
        
        self.is_recording = True
        self.click_sequence = []
        self.recording_start_time = time.time()
        
        if self.on_status_change:
            self.on_status_change("正在录制... 按 ESC 停止")
        
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
        
        # 通知 UI 更新
        if self.on_recording_update:
            self.on_recording_update(self.click_sequence.copy())
    
    def _on_key_press(self, key):
        """键盘按键回调 - 按下 ESC 键停止录制"""
        if not self.is_recording:
            return
        
        try:
            if key == keyboard.Key.esc:
                self.stop_recording()
        except AttributeError:
            pass
    
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
