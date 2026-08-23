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
from utils.win_windows import WindowRect


def _win(title, left, top, right, bottom) -> WindowRect:
    """窗口矩形测试替身构造器"""
    return WindowRect(title=title, left=left, top=top, right=right, bottom=bottom)


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


class TestSimpleClicking(unittest.TestCase):
    """内置连点模式：无需录制序列，直接按配置连点（对标商业连点器）"""

    def setUp(self):
        self.mouse_mock = MagicMock()
        self.mouse_mock.position = (0, 0)
        self.engine = _fresh_engine(self.mouse_mock, MagicMock())
        # 最快节奏跑完循环，避免拖慢测试
        self.engine.update_config(interval_ms=1, hold_duration=0)

    def _run_and_wait(self, timeout=2.0):
        self.assertTrue(self.engine.start_simple_clicking())
        deadline = time.time() + timeout
        while self.engine.is_running and time.time() < deadline:
            time.sleep(0.01)
        self.assertFalse(self.engine.is_running, "内置连点未在限时内结束")

    def test_fixed_position_clicks_there(self):
        self.engine.set_fixed_position((123, 456))
        self.engine.update_config(repeat_count=3)
        self._run_and_wait()
        self.assertEqual(self.mouse_mock.press.call_count, 3)
        self.assertEqual(self.mouse_mock.release.call_count, 3)
        # 每次点击前都移动到固定位置
        self.assertEqual(self.mouse_mock.position, (123, 456))

    def test_follow_cursor_does_not_move_mouse(self):
        # fixed_position=None：跟随光标，不写 position
        self.engine.update_config(repeat_count=2)
        self._run_and_wait()
        self.assertEqual(self.mouse_mock.press.call_count, 2)
        self.assertEqual(self.mouse_mock.position, (0, 0))  # 原地未动

    def test_double_click_type_presses_twice_per_event(self):
        self.engine.set_fixed_position((5, 5))
        self.engine.update_config(click_type='double', repeat_count=1)
        self._run_and_wait()
        self.assertEqual(self.mouse_mock.press.call_count, 2)
        self.assertEqual(self.mouse_mock.release.call_count, 2)

    def test_triple_click_type_presses_three_times(self):
        self.engine.update_config(click_type='triple', repeat_count=1,
                                  interval_ms=1)
        self._run_and_wait()
        self.assertEqual(self.mouse_mock.press.call_count, 3)

    def test_infinite_until_stopped(self):
        self.engine.set_fixed_position((7, 7))
        self.engine.update_config(repeat_count=0, interval_ms=1)
        self.assertTrue(self.engine.start_simple_clicking())
        deadline = time.time() + 2.0
        while self.mouse_mock.press.call_count < 5 and time.time() < deadline:
            time.sleep(0.005)
        self.assertGreaterEqual(self.mouse_mock.press.call_count, 5)
        self.engine.stop_clicking()
        time.sleep(0.05)
        self.assertFalse(self.engine.is_running)

    def test_start_simple_idempotent_while_running(self):
        self.engine.update_config(repeat_count=0, interval_ms=50)
        self.assertTrue(self.engine.start_simple_clicking())
        try:
            self.assertFalse(self.engine.start_simple_clicking())
        finally:
            self.engine.stop_clicking()
            time.sleep(0.05)

    def test_invalid_click_type_ignored(self):
        self.engine.update_config(click_type='quadruple')
        self.assertEqual(self.engine.click_type, 'single')

    def test_set_fixed_position_none_follows_cursor(self):
        self.engine.set_fixed_position((9, 9))
        self.engine.set_fixed_position(None)
        self.assertIsNone(self.engine.fixed_position)


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

    def test_anchor_roundtrip_via_dict(self):
        action = ClickAction(110, 120, 'left', 'press', 0.5,
                             anchor_title='记事本', win_rel_x=10, win_rel_y=20)
        restored = ClickAction.from_dict(action.to_dict())
        self.assertEqual(restored.anchor_title, '记事本')
        self.assertEqual((restored.win_rel_x, restored.win_rel_y), (10, 20))

    def test_legacy_dict_without_anchor(self):
        restored = ClickAction.from_dict(
            {'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press'})
        self.assertIsNone(restored.anchor_title)
        self.assertIsNone(restored.win_rel_x)


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


class TestAnchorRecording(unittest.TestCase):
    """窗口锚定录制：点击落在前台窗口客户区内时记录标题与相对偏移"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.is_recording = True
        self.engine.recording_start_time = time.time()
        self.engine.click_sequence = []
        self.engine.foreground_provider = (
            lambda: _win('记事本 - 无标题', 100, 50, 600, 400))

    def _click(self, x, y):
        from pynput import mouse
        self.engine._on_mouse_click(x, y, mouse.Button.left, True)

    def test_click_inside_window_captures_anchor(self):
        self._click(150, 100)
        action = self.engine.click_sequence[0]
        self.assertEqual(action.anchor_title, '记事本 - 无标题')
        self.assertEqual(action.win_rel_x, 50)   # 150-100
        self.assertEqual(action.win_rel_y, 50)   # 100-50
        # 绝对坐标仍保留，供降级路径使用
        self.assertEqual((action.x, action.y), (150, 100))

    def test_click_outside_window_no_anchor(self):
        self.engine.foreground_provider = (
            lambda: _win('记事本', 1000, 1000, 1400, 1300))
        self._click(150, 100)
        action = self.engine.click_sequence[0]
        self.assertIsNone(action.anchor_title)
        self.assertIsNone(action.win_rel_x)

    def test_provider_none_no_anchor(self):
        self.engine.foreground_provider = lambda: None
        self._click(150, 100)
        self.assertIsNone(self.engine.click_sequence[0].anchor_title)

    def test_provider_exception_does_not_break_recording(self):
        def boom():
            raise RuntimeError('win32 unavailable')
        self.engine.foreground_provider = boom
        self._click(150, 100)
        self.assertEqual(len(self.engine.click_sequence), 1)
        self.assertIsNone(self.engine.click_sequence[0].anchor_title)


class TestAnchorPlayback(unittest.TestCase):
    """窗口锚定回放：按同名窗口当前位置重算绝对坐标；找不到降级+警告"""

    def setUp(self):
        self.fake_mouse = _FakeMouseController()
        self.engine = _fresh_engine(self.fake_mouse, MagicMock())
        self.status_messages: list = []
        self.engine.on_status_change = self.status_messages.append

    def _anchored_sequence(self):
        return [
            ClickAction(110, 120, 'left', 'press', 0.0,
                        win_rel_x=10, win_rel_y=20, anchor_title='记事本'),
            ClickAction(110, 120, 'left', 'release', 0.1,
                        win_rel_x=10, win_rel_y=20, anchor_title='记事本'),
        ]

    def _run(self):
        self.assertTrue(self.engine.start_clicking())
        deadline = time.perf_counter() + 3.0
        while self.engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)

    def test_repositions_to_moved_window(self):
        # 录制时窗口在 (100,100)，回放时挪到 (200,300)：相对偏移应保持
        self.engine.window_locater = (
            lambda title: _win(title, 200, 300, 700, 600))
        self.engine.click_sequence = self._anchored_sequence()
        self.engine.update_config(hold_duration=0, interval_ms=0, repeat_count=1)
        self._run()
        moves = [op[1] for op in self.fake_mouse.ops if op[0] == 'move']
        self.assertEqual(moves[0], (210, 320))  # 200+10, 300+20

    def test_missing_window_falls_back_and_warns_once(self):
        self.engine.window_locater = lambda title: None
        self.engine.click_sequence = self._anchored_sequence()
        self.engine.update_config(hold_duration=0, interval_ms=0, repeat_count=1)
        self._run()
        # 降级：按录制时的绝对坐标执行
        moves = [op[1] for op in self.fake_mouse.ops if op[0] == 'move']
        self.assertEqual(moves[0], (110, 120))
        # 同一标题只警告一次
        warnings = [m for m in self.status_messages if '记事本' in m]
        self.assertEqual(len(warnings), 1)
        self.assertIn('未找到窗口', warnings[0])

    def test_unanchored_action_no_warning(self):
        self.engine.window_locater = lambda title: None
        self.engine.click_sequence = [
            ClickAction(55, 66, 'left', 'press', 0.0),
            ClickAction(55, 66, 'left', 'release', 0.05),
        ]
        self.engine.update_config(hold_duration=0, interval_ms=0, repeat_count=1)
        self._run()
        warnings = [m for m in self.status_messages if '未找到窗口' in m]
        self.assertEqual(warnings, [])


class TestTrajectoryRecording(unittest.TestCase):
    """拖拽轨迹录制：仅按键期间采样，双阈值（5px / 30ms）过滤"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.is_recording = True
        self.engine.recording_start_time = time.time()
        self.engine.click_sequence = []
        self.engine.foreground_provider = (
            lambda: _win('记事本', 0, 0, 1000, 800))

    def _click(self, x, y, pressed):
        from pynput import mouse
        self.engine._on_mouse_click(x, y, mouse.Button.left, pressed)

    def _moves(self):
        return [a for a in self.engine.click_sequence if a.kind == 'move']

    def test_only_records_while_button_down(self):
        self.engine._on_mouse_move(50, 50)          # 未按下 -> 忽略
        self.assertEqual(len(self._moves()), 0)
        self._click(10, 10, True)
        self.engine._last_move_time = time.time() - 0.05  # 通过时间门
        self.engine._on_mouse_move(300, 300)        # 按下后 -> 记录
        self.assertEqual(len(self._moves()), 1)

    def test_distance_threshold_filters_jitter(self):
        self._click(100, 100, True)
        self.engine._last_move_time = time.time() - 0.05
        self.engine._on_mouse_move(101, 101)        # 位移 ~1.4px < 5px
        self.assertEqual(len(self._moves()), 0)

    def test_interval_threshold_enforced(self):
        self._click(100, 100, True)
        self.engine._last_move_time = time.time() - 0.05
        self.engine._on_mouse_move(200, 200)        # 距离+间隔均足 -> 记录
        self.engine._on_mouse_move(400, 400)        # 距离够、间隔 <30ms -> 拦下
        self.assertEqual(len(self._moves()), 1)

    def test_far_and_slow_moves_recorded(self):
        self._click(100, 100, True)
        for x, y in ((150, 150), (250, 250), (350, 350)):
            self.engine._last_move_time = time.time() - 0.05  # 通过 30ms 门
            self.engine._on_mouse_move(x, y)
        self.assertEqual(len(self._moves()), 3)

    def test_no_sampling_after_release(self):
        self._click(100, 100, True)
        self.engine._last_move_time = time.time() - 0.05
        self.engine._on_mouse_move(200, 200)
        self._click(200, 200, False)
        self.engine._on_mouse_move(500, 500)        # 已释放 -> 忽略
        self.assertEqual(len(self._moves()), 1)

    def test_move_carries_anchor_and_timestamps_ordered(self):
        self._click(100, 100, True)
        self.engine._last_move_time = time.time() - 0.05
        self.engine._on_mouse_move(300, 300)
        move = self._moves()[0]
        self.assertEqual(move.anchor_title, '记事本')
        self.assertEqual((move.win_rel_x, move.win_rel_y), (300, 300))
        seq = self.engine.click_sequence
        self.assertLessEqual(seq[0].timestamp, seq[1].timestamp)


class TestMovePlayback(unittest.TestCase):
    """拖拽轨迹回放：press -> 移动点按序执行 -> release"""

    def setUp(self):
        self.fake_mouse = _FakeMouseController()
        self.engine = _fresh_engine(self.fake_mouse, MagicMock())

    def test_drag_replays_smooth_trajectory(self):
        self.engine.click_sequence = [
            ClickAction(100, 100, 'left', 'press', 0.0),
            ClickAction(110, 110, '', 'move', 0.05, kind='move'),
            ClickAction(130, 140, '', 'move', 0.10, kind='move'),
            ClickAction(130, 140, 'left', 'release', 0.15),
        ]
        self.engine.update_config(hold_duration=0, interval_ms=0,
                                  repeat_count=1)
        self.assertTrue(self.engine.start_clicking())
        deadline = time.perf_counter() + 3.0
        while self.engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)
        self.assertFalse(self.engine.is_running)
        self.assertEqual(
            self.fake_mouse.ops,
            [('move', (100, 100)), ('press',),
             ('move', (110, 110)), ('move', (130, 140)),
             ('move', (130, 140)), ('release',)]
        )

    def test_move_respects_window_anchor(self):
        self.engine.window_locater = (
            lambda title: _win(title, 500, 500, 1500, 1500))
        self.engine.click_sequence = [
            ClickAction(10, 20, '', 'move', 0.0, kind='move',
                        anchor_title='记事本', win_rel_x=10, win_rel_y=20),
        ]
        self.engine.update_config(interval_ms=0, repeat_count=1)
        self.assertTrue(self.engine.start_clicking())
        deadline = time.perf_counter() + 3.0
        while self.engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)
        self.assertIn(('move', (510, 520)), self.fake_mouse.ops)


class TestRemoveRange(unittest.TestCase):
    """区间删除：折叠轨迹行整段删除的引擎侧支撑"""

    def setUp(self):
        self.engine = _fresh_engine(MagicMock(), MagicMock())
        self.engine.click_sequence = [
            ClickAction(i, i, 'left', 'press', float(i)) for i in range(5)
        ]

    def test_remove_middle_range(self):
        removed = self.engine.remove_range(1, 3)
        self.assertEqual(removed, 3)
        self.assertEqual([a.x for a in self.engine.get_sequence()], [0, 4])

    def test_remove_invalid_range(self):
        self.assertEqual(self.engine.remove_range(3, 1), 0)
        self.assertEqual(self.engine.remove_range(-1, 2), 0)
        self.assertEqual(self.engine.remove_range(4, 9), 0)
        self.assertEqual(len(self.engine.get_sequence()), 5)


class TestDelayedStartAndAutoStop(unittest.TestCase):
    """延迟启动（等待期可停止）与自动停止时限"""

    def _wait_done(self, engine, timeout=5.0):
        deadline = time.perf_counter() + timeout
        while engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)

    def test_start_delay_waits_before_first_action(self):
        fake_mouse = _FakeMouseController()
        engine = _fresh_engine(fake_mouse, MagicMock())
        engine.click_sequence = [ClickAction(1, 1, 'left', 'press', 0.0)]
        engine.update_config(start_delay_s=0.4, interval_ms=0, repeat_count=1)
        started = time.perf_counter()
        self.assertTrue(engine.start_clicking())
        time.sleep(0.15)
        # 延迟窗口内尚未执行任何动作
        self.assertEqual(fake_mouse.ops, [])
        self.assertTrue(engine.is_running)
        self._wait_done(engine)
        elapsed = time.perf_counter() - started
        self.assertGreaterEqual(elapsed, 0.35)
        self.assertIn(('press',), fake_mouse.ops)

    def test_stop_during_delay_cancels_run(self):
        fake_mouse = _FakeMouseController()
        engine = _fresh_engine(fake_mouse, MagicMock())
        engine.click_sequence = [ClickAction(1, 1, 'left', 'press', 0.0)]
        engine.update_config(start_delay_s=2, interval_ms=0, repeat_count=1)
        self.assertTrue(engine.start_clicking())
        time.sleep(0.1)
        engine.stop_clicking()
        self._wait_done(engine)
        self.assertEqual(fake_mouse.ops, [])   # 延迟期内取消：未执行任何动作

    def test_auto_stop_terminates_long_run(self):
        fake_mouse = _FakeMouseController()
        engine = _fresh_engine(fake_mouse, MagicMock())
        # 配对点击 × 超大重复次数 -> 无限运行，靠 auto_stop 收束。
        # 注：时限检查在动作间隙生效；单条超长 hold 会阻塞到其自然结束。
        engine.click_sequence = [
            ClickAction(1, 1, 'left', 'press', 0.0),
            ClickAction(1, 1, 'left', 'release', 0.0),
        ]
        engine.update_config(hold_duration=0, interval_ms=20,
                             repeat_count=999999, auto_stop_s=0.3,
                             start_delay_s=0)
        started = time.perf_counter()
        self.assertTrue(engine.start_clicking())
        self._wait_done(engine, timeout=3.0)
        self.assertFalse(engine.is_running)
        elapsed = time.perf_counter() - started
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 2.0)
        # 确实执行过点击，且 press/release 成对收尾于时限内
        presses = fake_mouse.ops.count(('press',))
        releases = fake_mouse.ops.count(('release',))
        self.assertGreater(presses, 0)
        self.assertEqual(presses, releases)


class TestInfiniteRepeat(unittest.TestCase):
    """repeat_count<=0 表示无限循环，直到手动停止/自动停止"""

    def setUp(self):
        self.fake_mouse = _FakeMouseController()
        self.engine = _fresh_engine(self.fake_mouse, MagicMock())
        self.engine.click_sequence = [
            ClickAction(1, 1, 'left', 'press', 0.0),
            ClickAction(1, 1, 'left', 'release', 0.0),
        ]
        self.engine.update_config(hold_duration=0, interval_ms=15,
                                  repeat_interval=0, start_delay_s=0)

    def test_zero_repeat_runs_until_manual_stop(self):
        self.engine.update_config(repeat_count=0)  # 无限
        self.assertTrue(self.engine.start_clicking())
        time.sleep(0.12)
        presses_midway = self.fake_mouse.ops.count(('press',))
        self.assertGreaterEqual(presses_midway, 2)   # 已跑多轮
        self.assertTrue(self.engine.is_running)
        self.engine.stop_clicking()
        deadline = time.perf_counter() + 2.0
        while self.engine.is_running and time.perf_counter() < deadline:
            time.sleep(0.01)
        self.assertFalse(self.engine.is_running)
        # 手动停止后不再增长
        final = self.fake_mouse.ops.count(('press',))
        time.sleep(0.08)
        self.assertEqual(self.fake_mouse.ops.count(('press',)), final)

    def test_cursor_position_reported_during_recording(self):
        engine = _fresh_engine(MagicMock(), MagicMock())
        engine.is_recording = True
        engine.recording_start_time = time.time()
        messages = []
        engine.on_status_change = messages.append
        engine._on_mouse_move(111, 222)
        self.assertTrue(any('光标' in m and '111' in m for m in messages),
                        messages)
        # 节流：紧随其后的移动不再播报
        before = len(messages)
        engine._on_mouse_move(333, 444)
        self.assertEqual(len(messages), before)


class TestHotkeyButtonLabels(unittest.TestCase):
    """控制按钮文案随快捷键注入变化（OP 式"按钮上标热键"）"""

    def test_labels_reflect_hotkeys(self):
        import tkinter as tk
        from ui.components.control_buttons import ControlButtons
        root = tk.Tk(); root.withdraw()
        try:
            buttons = ControlButtons(root)
            buttons.set_hotkey_labels('f8', 'f10')
            self.assertEqual(buttons.click_button.cget('text'),
                             '开始点击 (F8)')
            self.assertEqual(buttons.record_button.cget('text'),
                             '开始录制 (F10)')
            buttons.update_clicking_state(True)
            self.assertEqual(buttons.click_button.cget('text'), '停止点击')
            buttons.update_clicking_state(False)
            self.assertIn('F8', buttons.click_button.cget('text'))
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
