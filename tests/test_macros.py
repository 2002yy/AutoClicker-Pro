"""
宏模块单元测试
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.macros import ClickAction, MacroRecorder, MacroPlayer, MacroStorage


class TestClickAction(unittest.TestCase):
    """测试 ClickAction 类"""
    
    def test_create_action(self):
        """测试创建点击动作"""
        action = ClickAction(100, 200, 'left', 'press', 1.5)
        self.assertEqual(action.x, 100)
        self.assertEqual(action.y, 200)
        self.assertEqual(action.button, 'left')
        self.assertEqual(action.action_type, 'press')
        self.assertEqual(action.timestamp, 1.5)
    
    def test_to_dict(self):
        """测试转换为字典"""
        action = ClickAction(100, 200, 'right', 'release', 2.0)
        data = action.to_dict()
        self.assertEqual(data['x'], 100)
        self.assertEqual(data['y'], 200)
        self.assertEqual(data['button'], 'right')
        self.assertEqual(data['action_type'], 'release')
        self.assertEqual(data['timestamp'], 2.0)
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {'x': 300, 'y': 400, 'button': 'middle', 'action_type': 'press', 'timestamp': 3.5}
        action = ClickAction.from_dict(data)
        self.assertEqual(action.x, 300)
        self.assertEqual(action.y, 400)
        self.assertEqual(action.button, 'middle')
        self.assertEqual(action.action_type, 'press')
        self.assertEqual(action.timestamp, 3.5)


class TestMacroRecorder(unittest.TestCase):
    """测试 MacroRecorder 类"""
    
    def setUp(self):
        self.recorder = MacroRecorder()
    
    def test_start_recording(self):
        """测试开始录制"""
        self.recorder.start_recording()
        self.assertTrue(self.recorder.is_recording)
        self.assertEqual(len(self.recorder.click_sequence), 0)
    
    def test_stop_recording(self):
        """测试停止录制"""
        self.recorder.start_recording()
        self.recorder.stop_recording()
        self.assertFalse(self.recorder.is_recording)
    
    def test_record_action(self):
        """测试记录动作"""
        self.recorder.start_recording()
        self.recorder.record_action(100, 200, 'left', 'press')
        self.recorder.record_action(100, 200, 'left', 'release')
        
        actions = self.recorder.get_sequence()
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].x, 100)
        self.assertEqual(actions[0].action_type, 'press')
        self.assertEqual(actions[1].action_type, 'release')
    
    def test_record_action_when_not_recording(self):
        """测试未录制时记录动作无效"""
        self.recorder.record_action(100, 200, 'left', 'press')
        self.assertEqual(len(self.recorder.get_sequence()), 0)
    
    def test_clear_sequence(self):
        """测试清空序列"""
        self.recorder.start_recording()
        self.recorder.record_action(100, 200, 'left', 'press')
        self.recorder.clear_sequence()
        self.assertEqual(len(self.recorder.get_sequence()), 0)
    
    def test_callback_on_action_recorded(self):
        """测试动作录制回调"""
        callback_called = False
        recorded_action = None
        
        def callback(action):
            nonlocal callback_called, recorded_action
            callback_called = True
            recorded_action = action
        
        self.recorder.on_action_recorded = callback
        self.recorder.start_recording()
        self.recorder.record_action(100, 200, 'left', 'press')
        
        self.assertTrue(callback_called)
        self.assertEqual(recorded_action.x, 100)


class TestMacroStorage(unittest.TestCase):
    """测试 MacroStorage 类"""
    
    def setUp(self):
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.storage = MacroStorage(self.test_dir)
        
        # 创建测试序列
        self.test_sequence = [
            ClickAction(100, 200, 'left', 'press', 0.1),
            ClickAction(100, 200, 'left', 'release', 0.2),
            ClickAction(300, 400, 'right', 'press', 0.5),
        ]
    
    def tearDown(self):
        # 清理临时目录
        shutil.rmtree(self.test_dir)
    
    def test_save_and_load_macro(self):
        """测试保存和加载宏"""
        self.storage.save_macro('test_macro', self.test_sequence)
        
        loaded_sequence = self.storage.load_macro('test_macro')
        self.assertEqual(len(loaded_sequence), len(self.test_sequence))
        for orig, loaded in zip(self.test_sequence, loaded_sequence):
            self.assertEqual(orig.x, loaded.x)
            self.assertEqual(orig.y, loaded.y)
            self.assertEqual(orig.button, loaded.button)
    
    def test_list_macros(self):
        """测试列出宏"""
        self.storage.save_macro('macro1', self.test_sequence)
        self.storage.save_macro('macro2', self.test_sequence)
        
        macros = self.storage.list_macros()
        self.assertIn('macro1', macros)
        self.assertIn('macro2', macros)
        self.assertEqual(len(macros), 2)
    
    def test_delete_macro(self):
        """测试删除宏"""
        self.storage.save_macro('test_macro', self.test_sequence)
        result = self.storage.delete_macro('test_macro')
        self.assertTrue(result)
        
        macros = self.storage.list_macros()
        self.assertNotIn('test_macro', macros)
    
    def test_delete_nonexistent_macro(self):
        """测试删除不存在的宏"""
        result = self.storage.delete_macro('nonexistent')
        self.assertFalse(result)
    
    def test_load_nonexistent_macro(self):
        """测试加载不存在的宏"""
        with self.assertRaises(FileNotFoundError):
            self.storage.load_macro('nonexistent')
    
    def test_save_and_load_encrypted_macro(self):
        """测试加密保存和加载宏"""
        password = 'test_password_123'
        self.storage.save_macro('encrypted_macro', self.test_sequence, password=password)
        
        # 没有密码应该失败
        with self.assertRaises(ValueError):
            self.storage.load_macro('encrypted_macro')
        
        # 有密码应该成功
        loaded_sequence = self.storage.load_macro('encrypted_macro', password=password)
        self.assertEqual(len(loaded_sequence), len(self.test_sequence))
        for orig, loaded in zip(self.test_sequence, loaded_sequence):
            self.assertEqual(orig.x, loaded.x)
            self.assertEqual(orig.y, loaded.y)


if __name__ == '__main__':
    unittest.main()
