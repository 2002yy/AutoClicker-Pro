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


if __name__ == '__main__':
    unittest.main()
