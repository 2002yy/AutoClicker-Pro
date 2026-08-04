"""
宏数据模型单元测试

说明：MacroRecorder / MacroPlayer / MacroStorage 已随死代码清理一并移除，
对应测试同步删除；录制/回放/存盘的行为由 tests/test_engine.py 覆盖。
"""

import unittest
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.macros import ClickAction


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

    def test_dict_roundtrip(self):
        """测试字典往返转换保持一致"""
        original = ClickAction(12, 34, 'x1', 'release', 0.75)
        restored = ClickAction.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_key_action_roundtrip(self):
        """键盘动作（kind/key）也应往返一致"""
        original = ClickAction(0, 0, '', 'press', 0.5, kind='key', key='enter')
        restored = ClickAction.from_dict(original.to_dict())
        self.assertEqual(original, restored)
        self.assertEqual(restored.kind, 'key')
        self.assertEqual(restored.key, 'enter')

    def test_from_dict_backward_compat(self):
        """旧数据无 kind/key 字段时，默认视为鼠标动作"""
        data = {'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press', 'timestamp': 0.0}
        a = ClickAction.from_dict(data)
        self.assertEqual(a.kind, 'mouse')
        self.assertIsNone(a.key)


if __name__ == '__main__':
    unittest.main()
