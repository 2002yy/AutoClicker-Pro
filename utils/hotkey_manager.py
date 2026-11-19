"""
快捷键管理模块
负责全局快捷键的注册、监听和管理
"""

import threading
from typing import Dict, Callable, Optional, List
from pynput import keyboard
from config.validation import normalize_hotkey, normalize_hotkey_key


class HotkeyManager:
    """全局快捷键管理器"""
    
    def __init__(self):
        self._hotkeys: Dict[str, Callable] = {}
        self._allow_extra_keys: set = set()
        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False
        self._lock = threading.Lock()
        self._pressed_keys: set = set()
    
    def register_hotkey(self, key_combination: str, callback: Callable,
                        *, allow_extra_keys: bool = False):
        """
        注册快捷键
        
        Args:
            key_combination: 快捷键组合，如 'f8', 'ctrl+shift+s'
            callback: 回调函数
        """
        with self._lock:
            hotkey = normalize_hotkey(key_combination)
            self._hotkeys[hotkey] = callback
            if allow_extra_keys:
                self._allow_extra_keys.add(hotkey)
            else:
                self._allow_extra_keys.discard(hotkey)
    
    def unregister_hotkey(self, key_combination: str):
        """注销快捷键"""
        with self._lock:
            hotkey = normalize_hotkey(key_combination)
            self._hotkeys.pop(hotkey, None)
            self._allow_extra_keys.discard(hotkey)
    
    def start(self):
        """开始监听快捷键"""
        with self._lock:
            if self._is_running:
                return
            
            self._is_running = True
            self._pressed_keys.clear()
        
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
    
    def stop(self):
        """停止监听"""
        with self._lock:
            self._is_running = False
        
        if self._listener:
            self._listener.stop()
            self._listener = None
    
    def _on_press(self, key):
        """按键按下事件"""
        if not self._is_running:
            return
        
        key_name = self._get_key_name(key)
        if not key_name:
            return
        
        with self._lock:
            # 操作系统在长按时会持续投递 on_press，这里去重，
            # 避免一次按住 F8 触发几十次回调。
            if key_name in self._pressed_keys:
                return
            self._pressed_keys.add(key_name)
        
        # 检查是否匹配任何注册的快捷键
        self._check_hotkeys(key_name)
    
    def _on_release(self, key):
        """按键释放事件"""
        key_name = self._get_key_name(key)
        if key_name:
            with self._lock:
                self._pressed_keys.discard(key_name)
    
    def _get_key_name(self, key) -> Optional[str]:
        """获取按键名称"""
        try:
            # 普通字符键
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            # 特殊功能键
            elif hasattr(key, 'name') and key.name:
                return key.name.lower()
        except AttributeError:
            pass
        return None
    
    def _check_hotkeys(self, pressed_key: str):
        """检查是否匹配任何注册的快捷键"""
        with self._lock:
            # 保留左右键各自的按下状态，只在匹配时合并成通用键名；
            # 左右 Ctrl 同时按住、仅松开一侧时另一侧仍然有效。
            current_keys = frozenset(normalize_hotkey_key(k) for k in self._pressed_keys)
            newly_pressed = normalize_hotkey_key(pressed_key)
            matched = [
                cb for hotkey, cb in self._hotkeys.items()
                if (frozenset(hotkey.split('+')) == current_keys
                    or (hotkey in self._allow_extra_keys
                        and newly_pressed in hotkey.split('+')
                        and frozenset(hotkey.split('+')).issubset(current_keys)))
            ]

        for callback in matched:
            # 在新线程中执行回调，避免阻塞监听；
            # 异常在子线程内捕获，避免默认 excepthook 把 traceback 刷进 stderr
            threading.Thread(
                target=self._safe_invoke, args=(callback,), daemon=True
            ).start()

    @staticmethod
    def _safe_invoke(callback: Callable):
        """执行单个快捷键回调并吞掉异常（容错优先，单次失败不影响监听）"""
        try:
            callback()
        except Exception as e:
            print(f"执行快捷键回调失败：{e}")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running
    
    def get_registered_hotkeys(self) -> List[str]:
        """获取所有已注册的快捷键"""
        with self._lock:
            return list(self._hotkeys.keys())
