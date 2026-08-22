"""
ClickerEngine 单元测试（应用真正使用的核心）

通过 mock pynput 控制器避免真实鼠标/键盘操作；save/load 测试将密钥目录
重定向到临时目录，避免污染用户主目录。
"""

import os
import sys
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine import ClickerEngine, ClickAction
from config.encryption import EncryptionManager
from config.validation import validate_macro_sequence


def _fresh_engine(mouse_mock, kb_mock):
    """构造一个使用 mock 控制器的引擎"""
    with patch('pynput.mouse.Controller', return_value=mouse_mock), \
         patch('pynput.keyboard.Controller', return_value=kb_mock):
        return ClickerEngine()


class TestClickerEngineConfig(unittest.TestCase):
    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())

    def test_default_config(self):
        self.assertEqual(self.engine.interval_ms, 100)
        self.assertEqual(self.engine.repeat_count, 1)
        self.assertEqual(self.engine.hold_duration, 100)

    def test_update_config(self):
        self.engine.update_config(interval_ms=50, repeat_count=5, hold_duration=0)
        self.assertEqual(self.engine.interval_ms, 50)
        self.assertEqual(self.engine.repeat_count, 5)
        self.assertEqual(self.engine.hold_duration, 0)

    def test_is_running_thread_safe(self):
        self.assertFalse(self.engine.is_running)
        self.engine.is_running = True
        self.assertTrue(self.engine.is_running)
        self.engine.is_running = False
        self.assertFalse(self.engine.is_running)


class TestClickerEngineClicking(unittest.TestCase):
    def setUp(self):
        self.mouse_mock = MagicMock()
        self.engine = _fresh_engine(self.mouse_mock, MagicMock())
        self.engine.click_sequence = [
            ClickAction(10, 20, 'left', 'press', 0.0),
            ClickAction(10, 20, 'left', 'release', 0.1),
        ]

    def test_execute_calls_mouse_controller(self):
        # hold_duration=0：press 动作只按下，release 动作负责释放
        self.engine.update_config(hold_duration=0, interval_ms=0, repeat_count=1)
        ok = self.engine.start_clicking()
        self.assertTrue(ok)
        time.sleep(0.3)  # 等待后台线程完成
        self.mouse_mock.press.assert_called()
        self.mouse_mock.release.assert_called()
        self.assertFalse(self.engine.is_running)  # finally 中已停止

    def test_start_clicking_idempotent(self):
        # 让点击动作保持运行（按住 500ms），在此期间再次调用应返回 False
        self.engine.update_config(hold_duration=500, interval_ms=0, repeat_count=1)
        self.assertTrue(self.engine.start_clicking())
        # 线程仍处于按住窗口期，is_running 为 True
        self.assertFalse(self.engine.start_clicking())
        time.sleep(0.7)  # 等待线程结束并复位状态
        self.assertFalse(self.engine.is_running)


class TestClickerEngineRecordingFilter(unittest.TestCase):
    """录制过滤钩子：落在本程序窗口内的点击不应入序列"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.is_recording = True
        self.engine.recording_start_time = time.time()
        self.engine.click_sequence = []

    def _click(self, x, y):
        from pynput import mouse
        self.engine._on_mouse_click(x, y, mouse.Button.left, True)

    def test_records_click_without_filter(self):
        self._click(500, 600)
        self.assertEqual(len(self.engine.click_sequence), 1)
        self.assertEqual(self.engine.click_sequence[0].x, 500)

    def test_filtered_click_is_skipped(self):
        # 模拟窗口矩形 (0,0)-(450,650)
        self.engine.ignore_click_predicate = lambda x, y: 0 <= x <= 450 and 0 <= y <= 650
        self._click(100, 100)   # 窗口内 -> 忽略
        self.assertEqual(len(self.engine.click_sequence), 0)
        self._click(900, 900)   # 窗口外 -> 录制
        self.assertEqual(len(self.engine.click_sequence), 1)
        self.assertEqual(self.engine.click_sequence[0].x, 900)

    def test_filter_exception_does_not_break_recording(self):
        def boom(x, y):
            raise RuntimeError("predicate failed")

        self.engine.ignore_click_predicate = boom
        self._click(10, 10)  # 过滤器异常时应降级为"照常录制"
        self.assertEqual(len(self.engine.click_sequence), 1)

    def test_no_recording_when_stopped(self):
        self.engine.is_recording = False
        self._click(10, 10)
        self.assertEqual(len(self.engine.click_sequence), 0)


class TestClickerEngineSaveLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # 将 EncryptionManager 的密钥目录重定向到临时目录
        EncryptionManager._instance = None
        with patch('pynput.mouse.Controller', return_value=MagicMock()), \
             patch('pynput.keyboard.Controller', return_value=MagicMock()), \
             patch('config.encryption.os.path.expanduser', return_value=self.tmp):
            self.engine = ClickerEngine()
        self.engine.click_sequence = [ClickAction(1, 2, 'left', 'press', 0.0)]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_load_roundtrip(self):
        p = os.path.join(self.tmp, 'seq.enc')
        self.engine.save_sequence(p)
        self.assertTrue(os.path.exists(p))

        self.engine.click_sequence = []
        self.engine.load_sequence(p)
        self.assertEqual(len(self.engine.click_sequence), 1)
        self.assertEqual(self.engine.click_sequence[0].x, 1)
        self.assertEqual(self.engine.click_sequence[0].button, 'left')

    def test_load_garbage_rejected(self):
        # 写入既非合法明文 JSON、也非合法加密体的内容，加载应失败
        p = os.path.join(self.tmp, 'bad.enc')
        with open(p, 'w', encoding='utf-8') as f:
            f.write("not a valid macro file")
        with self.assertRaises(Exception):
            self.engine.load_sequence(p)


class TestMacroValidation(unittest.TestCase):
    def test_rejects_missing_fields(self):
        ok, _ = validate_macro_sequence([{"x": 1}])  # 缺 y/button/action_type
        self.assertFalse(ok)

    def test_accepts_valid_action(self):
        ok, _ = validate_macro_sequence(
            [{"x": 1, "y": 2, "button": "left", "action_type": "press"}]
        )
        self.assertTrue(ok)

    def test_accepts_valid_key_action(self):
        ok, _ = validate_macro_sequence(
            [{"kind": "key", "key": "a", "action_type": "press", "timestamp": 0.0}]
        )
        self.assertTrue(ok)

    def test_rejects_key_action_without_key(self):
        ok, _ = validate_macro_sequence(
            [{"kind": "key", "action_type": "press"}]
        )
        self.assertFalse(ok)

    def test_rejects_invalid_key_name_in_old_format(self):
        # 旧格式（无 kind）仍按鼠标校验：button 非法应被拒
        ok, _ = validate_macro_sequence(
            [{"x": 1, "y": 2, "button": "space", "action_type": "press"}]
        )
        self.assertFalse(ok)


class TestClickerEngineKeyboardRecording(unittest.TestCase):
    """F2：录制应捕获键盘按键为 key 动作（ESC/全局快捷键除外）"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.is_recording = True
        self.engine.recording_start_time = time.time()
        self.engine.click_sequence = []

    def _press(self, key):
        self.engine._on_key_press(key)

    def test_records_normal_key(self):
        from pynput import keyboard
        self._press(keyboard.KeyCode(char='a'))
        self.assertEqual(len(self.engine.click_sequence), 1)
        a = self.engine.click_sequence[0]
        self.assertEqual(a.kind, 'key')
        self.assertEqual(a.key, 'a')
        self.assertEqual(a.action_type, 'press')

    def test_special_key_name(self):
        from pynput import keyboard
        self._press(keyboard.Key.enter)
        self.assertEqual(self.engine.click_sequence[0].key, 'enter')

    def test_esc_stops_recording(self):
        from pynput import keyboard
        self._press(keyboard.Key.esc)
        self.assertFalse(self.engine.is_recording)

    def test_hotkey_keys_skipped(self):
        from pynput import keyboard
        self._press(keyboard.Key.f8)
        self._press(keyboard.Key.f10)
        self._press(keyboard.Key.f11)
        self.assertEqual(len(self.engine.click_sequence), 0)

    def test_no_recording_when_stopped(self):
        from pynput import keyboard
        self.engine.is_recording = False
        self._press(keyboard.KeyCode(char='b'))
        self.assertEqual(len(self.engine.click_sequence), 0)

    def test_recording_update_notified(self):
        from pynput import keyboard
        captured = []
        self.engine.on_recording_update = lambda seq: captured.append(len(seq))
        self._press(keyboard.KeyCode(char='x'))
        self.assertEqual(captured, [1])


class TestClickerEngineKeyboardPlayback(unittest.TestCase):
    """F1：回放应把 key 动作发送到 keyboard_controller（轻点 / 按住）"""

    def setUp(self):
        self.kb_mock = MagicMock()
        self.engine = _fresh_engine(MagicMock(), self.kb_mock)
        self.engine.click_sequence = [
            ClickAction(0, 0, '', 'press', 0.0, kind='key', key='a'),
            ClickAction(10, 20, 'left', 'press', 0.1),
        ]

    def _pressed_chars(self):
        return [getattr(c.args[0], 'char', None)
                for c in self.kb_mock.press.call_args_list]

    def _released_chars(self):
        return [getattr(c.args[0], 'char', None)
                for c in self.kb_mock.release.call_args_list]

    def test_key_action_taps(self):
        from pynput import keyboard
        self.engine.update_config(hold_duration=0, interval_ms=0, repeat_count=1)
        self.engine.start_clicking()
        time.sleep(0.3)
        self.assertIn('a', self._pressed_chars())
        self.assertIn('a', self._released_chars())
        self.assertFalse(self.engine.is_running)

    def test_key_hold_duration(self):
        # 单个 key 动作 + 较长按住：按下后尚未释放；到时后才释放
        self.engine.click_sequence = [
            ClickAction(0, 0, '', 'press', 0.0, kind='key', key='a')
        ]
        self.engine.update_config(hold_duration=300, interval_ms=0, repeat_count=1)
        self.engine.start_clicking()
        time.sleep(0.1)
        self.assertIn('a', self._pressed_chars())
        self.assertNotIn('a', self._released_chars())  # 仍在按住
        time.sleep(0.4)
        self.assertIn('a', self._released_chars())      # 到点释放


class TestChordRecording(unittest.TestCase):
    """组合键录制：修饰键挂起，触发键到达时录为单条 chord"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.is_recording = True
        self.engine.recording_start_time = time.time()
        self.engine.click_sequence = []

    def _press(self, key):
        self.engine._on_key_press(key)

    def _release(self, key):
        self.engine._on_key_release(key)

    def test_ctrl_c_records_single_chord(self):
        from pynput import keyboard
        self._press(keyboard.Key.ctrl_l)
        self.assertEqual(len(self.engine.click_sequence), 0)  # 挂起中不录
        self._press(keyboard.KeyCode(char='c'))
        self.assertEqual(len(self.engine.click_sequence), 1)
        action = self.engine.click_sequence[0]
        self.assertEqual(action.kind, 'chord')
        self.assertEqual(action.key, 'c')
        self.assertEqual(action.modifiers, ['ctrl_l'])

    def test_consumed_modifier_release_emits_nothing(self):
        from pynput import keyboard
        self._press(keyboard.Key.ctrl_l)
        self._press(keyboard.KeyCode(char='c'))
        self._release(keyboard.Key.ctrl_l)
        self.assertEqual(len(self.engine.click_sequence), 1)

    def test_lone_modifier_tap_recorded_on_release(self):
        from pynput import keyboard
        # 注：pynput 中 Key.shift_l 的规范名就是 'shift'（左右 Shift 共享）
        self._press(keyboard.Key.shift)
        self.assertEqual(len(self.engine.click_sequence), 0)  # 挂起中
        self._release(keyboard.Key.shift)
        self.assertEqual(len(self.engine.click_sequence), 1)
        action = self.engine.click_sequence[0]
        self.assertEqual(action.kind, 'key')
        self.assertEqual(action.key, 'shift')

    def test_modifier_plus_mouse_click(self):
        from pynput import keyboard, mouse
        self._press(keyboard.Key.ctrl_l)
        self.engine._on_mouse_click(100, 200, mouse.Button.left, True)
        self.engine._on_mouse_click(100, 200, mouse.Button.left, False)
        press_action, release_action = self.engine.click_sequence[:2]
        self.assertEqual(press_action.modifiers, ['ctrl_l'])
        self.assertEqual(release_action.modifiers, ['ctrl_l'])
        # ctrl 物理释放后已被消费，不再补录
        self._release(keyboard.Key.ctrl_l)
        self.assertEqual(len(self.engine.click_sequence), 2)

    def test_stop_discards_pending_modifiers(self):
        from pynput import keyboard
        self._press(keyboard.Key.alt_l)
        self.engine.stop_recording()
        self.assertFalse(self.engine.is_recording)
        self.assertEqual(len(self.engine.click_sequence), 0)


class _FakeMouseController:
    """记录操作序列的假鼠标控制器（用于验证拖拽的移动-按下-移动-释放顺序）"""

    def __init__(self):
        self.ops = []
        self._position = None

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self.ops.append(('move', value))
        self._position = value

    def press(self, button):
        self.ops.append(('press',))

    def release(self, button):
        self.ops.append(('release',))


class TestDragPairing(unittest.TestCase):
    """拖拽修复：配对的 press 不注入 hold_duration 自动释放"""

    def setUp(self):
        self.fake_mouse = _FakeMouseController()
        self.engine = _fresh_engine(self.fake_mouse, MagicMock())
        self.engine.click_sequence = [
            ClickAction(10, 20, 'left', 'press', 0.0),
            ClickAction(30, 40, 'left', 'release', 0.15),
        ]

    def test_drag_survives_large_hold_duration(self):
        # 旧实现在此配置下会把拖拽拆成"原地按下-等5秒-原地释放"
        self.engine.update_config(hold_duration=5000, interval_ms=0,
                                  repeat_count=1)
        started = time.time()
        self.assertTrue(self.engine.start_clicking())
        deadline = started + 3.0
        while self.engine.is_running and time.time() < deadline:
            time.sleep(0.02)
        self.assertFalse(self.engine.is_running)

        # 完成耗时应远小于 hold_duration（时间轴上 0.15s 处释放）
        self.assertLess(time.time() - started, 2.0)

        # 操作序列必须是：移动A -> 按下 -> 移动B -> 释放（真实拖拽语义）
        self.assertEqual(
            self.fake_mouse.ops,
            [('move', (10, 20)), ('press',), ('move', (30, 40)), ('release',)]
        )

    def test_unpaired_press_still_taps_with_hold(self):
        # 孤立 press（无对应 release）保持轻点 + hold_duration 语义
        self.fake_mouse.ops = []
        self.engine.click_sequence = [ClickAction(1, 2, 'left', 'press', 0.0)]
        self.engine.update_config(hold_duration=200, interval_ms=0,
                                  repeat_count=1)
        self.assertTrue(self.engine.start_clicking())
        time.sleep(0.05)
        self.assertIn(('press',), self.fake_mouse.ops)
        self.assertNotIn(('release',), self.fake_mouse.ops)  # 按住中
        time.sleep(0.35)
        self.assertIn(('release',), self.fake_mouse.ops)     # 到点轻点完成


class TestChordPlayback(unittest.TestCase):
    """组合键回放：按住修饰键 -> 轻点触发键 -> 逆序释放修饰键"""

    def setUp(self):
        self.kb_mock = MagicMock()
        self.engine = _fresh_engine(MagicMock(), self.kb_mock)
        self.engine.click_sequence = [
            ClickAction(0, 0, '', 'press', 0.0, kind='chord',
                        key='c', modifiers=['ctrl_l']),
        ]

    def test_chord_press_order(self):
        from pynput import keyboard
        self.engine.update_config(hold_duration=0, interval_ms=0,
                                  repeat_count=1)
        self.assertTrue(self.engine.start_clicking())
        time.sleep(0.3)
        self.assertFalse(self.engine.is_running)

        pressed_names = []
        for call in self.kb_mock.press.call_args_list:
            k = call.args[0]
            pressed_names.append(getattr(k, 'name', None) or getattr(k, 'char'))
        released_names = []
        for call in self.kb_mock.release.call_args_list:
            k = call.args[0]
            released_names.append(getattr(k, 'name', None) or getattr(k, 'char'))

        self.assertEqual(pressed_names, ['ctrl_l', 'c'])
        # 触发键先于修饰键释放（逆序）
        self.assertEqual(released_names, ['c', 'ctrl_l'])


class _FakeKeyboardController:
    """记录按键时刻的假键盘控制器（用于验证时间戳时序）"""

    def __init__(self):
        self.press_times = []

    def press(self, key):
        self.press_times.append(time.perf_counter())

    def release(self, key):
        pass


class TestTimestampPacing(unittest.TestCase):
    """回放时序：有非零时间戳按原速；全零退回固定间隔"""

    def setUp(self):
        self.fake_kb = _FakeKeyboardController()
        self.engine = _fresh_engine(MagicMock(), self.fake_kb)
        self.engine.update_config(interval_ms=1000, repeat_count=1)

    def _run_and_collect_gaps(self):
        self.assertTrue(self.engine.start_clicking())
        deadline = time.perf_counter() + 5.0
        while self.engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)
        times = self.fake_kb.press_times
        return [times[i + 1] - times[i] for i in range(len(times) - 1)]

    def test_recorded_timestamps_replayed_at_original_speed(self):
        self.engine.click_sequence = [
            ClickAction(0, 0, '', 'press', 0.0, kind='key', key='a'),
            ClickAction(0, 0, '', 'press', 0.3, kind='key', key='b'),
        ]
        gaps = self._run_and_collect_gaps()
        self.assertEqual(len(gaps), 1)
        # 原速：间隔应接近录制的 0.3s（而非 interval_ms 的 1s 或 0s）
        self.assertGreaterEqual(gaps[0], 0.25)

    def test_zero_timestamps_fall_back_to_interval(self):
        self.engine.update_config(interval_ms=150)
        self.engine.click_sequence = [
            ClickAction(0, 0, '', 'press', 0.0, kind='key', key='a'),
            ClickAction(0, 0, '', 'press', 0.0, kind='key', key='b'),
        ]
        gaps = self._run_and_collect_gaps()
        self.assertEqual(len(gaps), 1)
        self.assertGreaterEqual(gaps[0], 0.12)


class TestModifiersModelRoundtrip(unittest.TestCase):
    """含 modifiers/chord 的动作经 to_dict/from_dict 与存取往返后保真"""

    def test_chord_roundtrip_via_dict(self):
        action = ClickAction(0, 0, '', 'press', 1.5, kind='chord',
                             key='v', modifiers=['ctrl_l', 'shift_r'])
        restored = ClickAction.from_dict(action.to_dict())
        self.assertEqual(restored.modifiers, ['ctrl_l', 'shift_r'])
        self.assertEqual(restored.kind, 'chord')

    def test_legacy_dict_without_modifiers(self):
        restored = ClickAction.from_dict(
            {'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press'}
        )
        self.assertEqual(restored.modifiers, [])


class TestSequenceEditing(unittest.TestCase):
    """序列编辑：删除 / 移动 / 清空（线程安全方法）"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.click_sequence = [
            ClickAction(1, 1, 'left', 'press', 0.0),
            ClickAction(2, 2, 'left', 'release', 0.1),
            ClickAction(3, 3, 'left', 'press', 0.2),
        ]

    def test_remove_action(self):
        self.assertTrue(self.engine.remove_action(1))
        self.assertEqual(len(self.engine.get_sequence()), 2)
        self.assertFalse(self.engine.remove_action(99))  # 越界
        self.assertEqual(len(self.engine.get_sequence()), 2)

    def test_move_action(self):
        self.assertTrue(self.engine.move_action(0, 2))
        seq = self.engine.get_sequence()
        self.assertEqual([a.x for a in seq], [2, 3, 1])
        self.assertFalse(self.engine.move_action(0, 5))   # 越界
        self.assertFalse(self.engine.move_action(1, 1))   # 原地

    def test_clear_sequence_notifies_ui(self):
        notified = []
        self.engine.on_recording_update = lambda seq: notified.append(len(seq))
        self.engine.clear_sequence()
        self.assertEqual(notified, [0])
        self.assertEqual(len(self.engine.get_sequence()), 0)

    def test_get_sequence_returns_copy(self):
        seq = self.engine.get_sequence()
        seq.clear()
        self.assertEqual(len(self.engine.get_sequence()), 3)


if __name__ == '__main__':
    unittest.main()
