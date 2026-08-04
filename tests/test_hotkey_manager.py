"""
快捷键管理器单元测试
"""

import unittest
import time
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.hotkey_manager import HotkeyManager


class TestHotkeyManager(unittest.TestCase):
    """测试 HotkeyManager 类"""
    
    def setUp(self):
        self.manager = HotkeyManager()
    
    def tearDown(self):
        if self.manager.is_running():
            self.manager.stop()
    
    def test_register_hotkey(self):
        """测试注册快捷键"""
        callback_called = False
        
        def callback():
            nonlocal callback_called
            callback_called = True
        
        self.manager.register_hotkey('f8', callback)
        hotkeys = self.manager.get_registered_hotkeys()
        
        self.assertIn('f8', hotkeys)
    
    def test_unregister_hotkey(self):
        """测试注销快捷键"""
        def callback():
            pass
        
        self.manager.register_hotkey('f9', callback)
        self.manager.unregister_hotkey('f9')
        hotkeys = self.manager.get_registered_hotkeys()
        
        self.assertNotIn('f9', hotkeys)
    
    def test_start_and_stop(self):
        """测试启动和停止"""
        self.manager.start()
        self.assertTrue(self.manager.is_running())
        
        self.manager.stop()
        self.assertFalse(self.manager.is_running())
    
    def test_double_start(self):
        """测试重复启动"""
        self.manager.start()
        self.assertTrue(self.manager.is_running())
        
        # 再次启动应该不会出错
        self.manager.start()
        self.assertTrue(self.manager.is_running())
        
        self.manager.stop()
    
    def test_get_key_name_char(self):
        """测试获取字符键名称"""
        from pynput.keyboard import Key
        
        # 模拟一个字符键
        class MockKey:
            char = 'a'
            name = None
        
        result = self.manager._get_key_name(MockKey())
        self.assertEqual(result, 'a')
    
    def test_get_key_name_special(self):
        """测试获取特殊键名称"""
        from pynput.keyboard import Key
        
        result = self.manager._get_key_name(Key.f1)
        self.assertEqual(result, 'f1')
    
    def test_multiple_hotkeys(self):
        """测试注册多个快捷键"""
        callbacks = {}
        
        for i in range(5):
            key = f'f{i+1}'
            called = False
            def make_callback():
                def callback():
                    nonlocal called
                    called = True
                return callback
            callbacks[key] = {'called': False, 'callback': make_callback()}
            self.manager.register_hotkey(key, callbacks[key]['callback'])
        
        hotkeys = self.manager.get_registered_hotkeys()
        self.assertEqual(len(hotkeys), 5)
        
        for i in range(5):
            key = f'f{i+1}'
            self.assertIn(key, hotkeys)


class _FakeKey:
    """模拟 pynput 的特殊功能键"""

    def __init__(self, name):
        self.name = name
        self.char = None


class TestHotkeyDispatch(unittest.TestCase):
    """测试按键分发与去抖（不启动真实监听器，直接驱动内部回调）"""

    def setUp(self):
        self.manager = HotkeyManager()
        self.manager._is_running = True  # 跳过真实 listener
        self.calls = []
        self.manager.register_hotkey('f8', lambda: self.calls.append('f8'))

    def _settle(self):
        # 回调在守护线程中执行，给它一点时间
        time.sleep(0.15)

    def test_press_triggers_callback(self):
        self.manager._on_press(_FakeKey('f8'))
        self._settle()
        self.assertEqual(self.calls, ['f8'])

    def test_key_repeat_is_debounced(self):
        """长按时操作系统会连发 on_press，应只触发一次"""
        for _ in range(10):
            self.manager._on_press(_FakeKey('f8'))
        self._settle()
        self.assertEqual(len(self.calls), 1)

    def test_release_then_press_triggers_again(self):
        self.manager._on_press(_FakeKey('f8'))
        self.manager._on_release(_FakeKey('f8'))
        self.manager._on_press(_FakeKey('f8'))
        self._settle()
        self.assertEqual(len(self.calls), 2)

    def test_unrelated_key_does_not_trigger(self):
        self.manager._on_press(_FakeKey('f7'))
        self._settle()
        self.assertEqual(self.calls, [])

    def test_extra_modifier_breaks_match(self):
        """f8 + ctrl 不应命中单键 f8"""
        self.manager._on_press(_FakeKey('ctrl_l'))
        self.manager._on_press(_FakeKey('f8'))
        self._settle()
        self.assertEqual(self.calls, [])

    def test_ignored_when_not_running(self):
        self.manager._is_running = False
        self.manager._on_press(_FakeKey('f8'))
        self._settle()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
