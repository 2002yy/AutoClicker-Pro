"""
快捷键管理模块
负责全局快捷键的注册、监听和管理
"""

import threading
from typing import Dict, Callable, Optional, List
from pynput import keyboard


class HotkeyManager:
    """全局快捷键管理器"""
    
    def __init__(self):
        self._hotkeys: Dict[str, Callable] = {}
        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False
        self._lock = threading.Lock()
        self._pressed_keys: set = set()
    
    def register_hotkey(self, key_combination: str, callback: Callable):
        """
        注册快捷键
        
        Args:
            key_combination: 快捷键组合，如 'f8', 'ctrl+shift+s'
            callback: 回调函数
        """
        with self._lock:
            self._hotkeys[key_combination.lower()] = callback
    
    def unregister_hotkey(self, key_combination: str):
        """注销快捷键"""
        with self._lock:
            if key_combination.lower() in self._hotkeys:
                del self._hotkeys[key_combination.lower()]
    
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
        
        # 获取按键名称
        key_name = self._get_key_name(key)
        if key_name:
            self._pressed_keys.add(key_name)
            
            # 检查是否匹配任何注册的快捷键
            self._check_hotkeys()
    
    def _on_release(self, key):
        """按键释放事件"""
        key_name = self._get_key_name(key)
        if key_name:
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
    
    def _check_hotkeys(self):
        """检查是否匹配任何注册的快捷键"""
        current_keys = frozenset(self._pressed_keys)
        
        for hotkey, callback in list(self._hotkeys.items()):
            # 解析快捷键组合
            key_parts = set(hotkey.split('+'))
            
            # 检查是否完全匹配
            if key_parts == current_keys:
                try:
                    # 在新线程中执行回调，避免阻塞监听
                    threading.Thread(target=callback, daemon=True).start()
                except Exception as e:
                    print(f"执行快捷键回调失败：{e}")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running
    
    def get_registered_hotkeys(self) -> List[str]:
        """获取所有已注册的快捷键"""
        with self._lock:
            return list(self._hotkeys.keys())
