"""
测试验证模块
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.validation import (
    validate_number,
    validate_string,
    validate_coordinate,
    validate_time_inputs,
    validate_macro_action,
    validate_macro_sequence
)


class TestValidation(unittest.TestCase):
    """测试验证功能"""
    
    def test_validate_number_valid(self):
        """测试有效数字验证"""
        is_valid, msg = validate_number(100, "测试字段", min_val=0, max_val=1000)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
    
    def test_validate_number_invalid_type(self):
        """测试无效类型"""
        is_valid, msg = validate_number("abc", "测试字段")
        self.assertFalse(is_valid)
        self.assertIn("必须是有效的数字", msg)
    
    def test_validate_number_below_min(self):
        """测试小于最小值"""
        is_valid, msg = validate_number(-5, "测试字段", min_val=0)
        self.assertFalse(is_valid)
        self.assertIn("不能小于", msg)
    
    def test_validate_number_above_max(self):
        """测试大于最大值"""
        is_valid, msg = validate_number(1001, "测试字段", max_val=1000)
        self.assertFalse(is_valid)
        self.assertIn("不能大于", msg)
    
    def test_validate_string_valid(self):
        """测试有效字符串验证"""
        is_valid, msg = validate_string("left", "按钮", allowed_values=['left', 'right'])
        self.assertTrue(is_valid)
    
    def test_validate_string_invalid_value(self):
        """测试无效的允许值"""
        is_valid, msg = validate_string("middle", "按钮", allowed_values=['left', 'right'])
        self.assertFalse(is_valid)
        self.assertIn("必须是以下值之一", msg)
    
    def test_validate_coordinate_valid(self):
        """测试有效坐标"""
        is_valid, msg = validate_coordinate(100, 200)
        self.assertTrue(is_valid)
    
    def test_validate_coordinate_negative(self):
        """测试负坐标"""
        is_valid, msg = validate_coordinate(-1, 100)
        self.assertFalse(is_valid)
    
    def test_validate_time_inputs_valid(self):
        """测试有效时间输入"""
        is_valid, msg = validate_time_inputs(100, 100, 100, 1, 1000)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
    
    def test_validate_time_inputs_invalid_interval(self):
        """测试无效间隔"""
        is_valid, msg = validate_time_inputs(0, 100, 100, 1, 1000)
        self.assertFalse(is_valid)
        self.assertIn("点击间隔", msg)
    
    def test_validate_macro_action_valid(self):
        """测试有效宏动作"""
        action = {
            'x': 100,
            'y': 200,
            'button': 'left',
            'action_type': 'press',
            'timestamp': 1.5
        }
        is_valid, msg = validate_macro_action(action)
        self.assertTrue(is_valid)
    
    def test_validate_macro_action_missing_field(self):
        """测试缺少字段的宏动作"""
        action = {
            'x': 100,
            'y': 200,
            # 缺少 button 和 action_type
        }
        is_valid, msg = validate_macro_action(action)
        self.assertFalse(is_valid)
        self.assertIn("缺少必需字段", msg)
    
    def test_validate_macro_sequence_valid(self):
        """测试有效宏序列"""
        actions = [
            {'x': 100, 'y': 200, 'button': 'left', 'action_type': 'press'},
            {'x': 100, 'y': 200, 'button': 'left', 'action_type': 'release'}
        ]
        is_valid, msg = validate_macro_sequence(actions)
        self.assertTrue(is_valid)
    
    def test_validate_macro_sequence_empty(self):
        """测试空宏序列"""
        is_valid, msg = validate_macro_sequence([])
        self.assertFalse(is_valid)
        self.assertIn("不能为空", msg)
    
    def test_validate_macro_sequence_not_list(self):
        """测试非列表宏序列"""
        is_valid, msg = validate_macro_sequence("not a list")
        self.assertFalse(is_valid)
        self.assertIn("必须是列表格式", msg)


class TestChordAndModifierValidation(unittest.TestCase):
    """组合键与修饰键校验"""

    def test_valid_chord_accepted(self):
        ok, msg = validate_macro_action({
            'kind': 'chord', 'key': 'c',
            'modifiers': ['ctrl_l'], 'action_type': 'press'
        })
        self.assertTrue(ok, msg)

    def test_chord_requires_modifiers(self):
        ok, _ = validate_macro_action(
            {'kind': 'chord', 'key': 'c', 'action_type': 'press'}
        )
        self.assertFalse(ok)

    def test_chord_rejects_invalid_modifier_name(self):
        ok, msg = validate_macro_action({
            'kind': 'chord', 'key': 'c',
            'modifiers': ['ctrl_l', 'notamod'], 'action_type': 'press'
        })
        self.assertFalse(ok)
        self.assertIn('notamod', msg)

    def test_chord_rejects_release(self):
        ok, _ = validate_macro_action({
            'kind': 'chord', 'key': 'c',
            'modifiers': ['ctrl'], 'action_type': 'release'
        })
        self.assertFalse(ok)

    def test_mouse_with_modifiers_accepted(self):
        ok, msg = validate_macro_action({
            'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press',
            'modifiers': ['shift']
        })
        self.assertTrue(ok, msg)

    def test_mouse_with_invalid_modifiers_rejected(self):
        ok, _ = validate_macro_action({
            'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press',
            'modifiers': ['f8']
        })
        self.assertFalse(ok)

    def test_is_modifier_name(self):
        from config.validation import is_modifier_name
        for name in ('ctrl', 'ctrl_l', 'alt_gr', 'shift', 'cmd'):
            self.assertTrue(is_modifier_name(name), name)
        for name in ('f8', 'enter', 'a', '', None, 'ctrll'):
            self.assertFalse(is_modifier_name(name))


class TestMoveValidation(unittest.TestCase):
    """移动轨迹动作（kind='move'）校验"""

    def test_valid_move_accepted(self):
        ok, msg = validate_macro_action(
            {'kind': 'move', 'x': 5, 'y': 6, 'timestamp': 0.1})
        self.assertTrue(ok, msg)

    def test_move_without_coords_rejected(self):
        ok, _ = validate_macro_action({'kind': 'move'})
        self.assertFalse(ok)

    def test_move_with_anchor_accepted(self):
        ok, msg = validate_macro_action({
            'kind': 'move', 'x': 5, 'y': 6,
            'anchor_title': '记事本', 'win_rel_x': 1, 'win_rel_y': 2})
        self.assertTrue(ok, msg)

    def test_move_negative_coord_rejected(self):
        ok, _ = validate_macro_action({'kind': 'move', 'x': -1, 'y': 2})
        self.assertFalse(ok)


class TestAnchorValidation(unittest.TestCase):
    """窗口锚定字段校验"""

    def _mouse(self, **extra):
        action = {'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press'}
        action.update(extra)
        return validate_macro_action(action)

    def test_full_anchor_fields_accepted(self):
        ok, msg = self._mouse(anchor_title='记事本', win_rel_x=10, win_rel_y=20)
        self.assertTrue(ok, msg)

    def test_no_anchor_fields_accepted(self):
        ok, msg = self._mouse()
        self.assertTrue(ok, msg)

    def test_partial_anchor_rejected(self):
        ok, _ = self._mouse(anchor_title='记事本', win_rel_x=10)  # 缺 rel_y
        self.assertFalse(ok)

    def test_empty_title_rejected(self):
        ok, _ = self._mouse(anchor_title='  ', win_rel_x=10, win_rel_y=20)
        self.assertFalse(ok)

    def test_non_int_rel_rejected(self):
        ok, _ = self._mouse(anchor_title='记事本', win_rel_x='a', win_rel_y=20)
        self.assertFalse(ok)
        ok, _ = self._mouse(anchor_title='记事本', win_rel_x=True, win_rel_y=20)
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
