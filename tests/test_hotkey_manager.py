"""
HotkeyManager 单元测试
覆盖注册、去重、组合键匹配、并发安全与异常回调。
"""

import threading
import unittest
from unittest.mock import MagicMock

from utils.hotkey_manager import HotkeyManager
from pynput import keyboard


def _make_key(name: str):
    """用真实的 keyboard.Key 构造一个按键对象；字符键用 keyboard.KeyCode。"""
    try:
        return getattr(keyboard.Key, name)
    except AttributeError:
        return keyboard.KeyCode(char=name)


class TestHotkeyManager(unittest.TestCase):
    """全局快捷键管理器测试"""

    def setUp(self):
        self.hm = HotkeyManager()

    def tearDown(self):
        self.hm.stop()

    # ---- 注册 / 注销 ----

    def test_register_and_get(self):
        cb = MagicMock()
        self.hm.register_hotkey("f8", cb)
        self.assertEqual(self.hm.get_registered_hotkeys(), ["f8"])

    def test_unregister(self):
        self.hm.register_hotkey("f8", MagicMock())
        self.assertEqual(self.hm.get_registered_hotkeys(), ["f8"])
        self.hm.unregister_hotkey("f8")
        self.assertEqual(self.hm.get_registered_hotkeys(), [])

    def test_case_insensitive_register(self):
        """注册 F8 后触发 f8 也能匹配（大小写不敏感）"""
        called = []
        self.hm.register_hotkey("F8", lambda: called.append(1))
        self.hm.start()
        self.hm._on_press(_make_key("f8"))
        self.assertEqual(called, [1])

    # ---- 去重（长按防抖）----

    def test_long_press_debounce(self):
        """连续两次 on_press 相同键只触发一次回调"""
        called = []
        self.hm.register_hotkey("f8", lambda: called.append(1))
        self.hm.start()
        key = _make_key("f8")
        self.hm._on_press(key)
        self.hm._on_press(key)  # 第二次应被去重
        self.assertEqual(called, [1])

    def test_release_clears_pressed(self):
        """释放后同一键可以再次触发"""
        called = []
        self.hm.register_hotkey("f8", lambda: called.append(1))
        self.hm.start()
        key = _make_key("f8")
        self.hm._on_press(key)
        self.hm._on_release(key)
        self.hm._on_press(key)  # 释放后重按应生效
        self.assertEqual(called, [1, 1])

    # ---- 组合键 ----

    def test_combo_key(self):
        """组合键 Ctrl+Shift+S 匹配"""
        called = []
        self.hm.register_hotkey("ctrl+shift+s", lambda: called.append(1))
        self.hm.start()
        for name in ("ctrl", "shift", "s"):
            self.hm._on_press(_make_key(name))
        self.assertEqual(called, [1])

    def test_combo_order_independent(self):
        """组合键按任意顺序按下都应匹配"""
        called = []
        self.hm.register_hotkey("ctrl+alt+f4", lambda: called.append(1))
        self.hm.start()
        for name in ("f4", "alt", "ctrl"):  # 逆序
            self.hm._on_press(_make_key(name))
        self.assertEqual(called, [1])

    # ---- 单键 ----

    def test_single_key_trigger(self):
        """单键 F8 触发"""
        called = []
        self.hm.register_hotkey("f8", lambda: called.append(1))
        self.hm.start()
        self.hm._on_press(_make_key("f8"))
        self.assertEqual(called, [1])

    # ---- 异常回调隔离 ----

    def test_callback_exception_does_not_crash_listener(self):
        """回调抛异常时 listener 继续存活"""
        self.hm.register_hotkey("f8", lambda: 1 / 0)
        self.hm.start()
        self.hm._on_press(_make_key("f8"))
        self.assertTrue(self.hm.is_running())

    # ---- 并发安全 ----

    def test_concurrent_press_release(self):
        """并发按下/释放不会抛异常"""
        called = []
        self.hm.register_hotkey("f8", lambda: called.append(1))
        self.hm.start()
        key = _make_key("f8")

        def press_release():
            for _ in range(10):
                self.hm._on_press(key)
                self.hm._on_release(key)

        threads = [threading.Thread(target=press_release) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(self.hm.is_running())


class TestHotkeyManagerIntegration(unittest.TestCase):
    """端到端：注册、触发、清理的完整生命周期"""

    def test_full_lifecycle(self):
        hm = HotkeyManager()
        callbacks = {"f8": [], "f10": [], "ctrl+s": []}

        hm.register_hotkey("f8", lambda: callbacks["f8"].append(1))
        hm.register_hotkey("f10", lambda: callbacks["f10"].append(1))
        hm.register_hotkey("ctrl+s", lambda: callbacks["ctrl+s"].append(1))

        hm.start()
        self.assertTrue(hm.is_running())

        # 触发 F8（按下 + 释放）
        hm._on_press(_make_key("f8"))
        hm._on_release(_make_key("f8"))
        self.assertEqual(callbacks["f8"], [1])
        self.assertEqual(callbacks["ctrl+s"], [])

        # 触发 Ctrl+S（按下 + 释放）
        ctrl = _make_key("ctrl")
        s = _make_key("s")
        hm._on_press(ctrl)
        hm._on_press(s)
        hm._on_release(ctrl)
        hm._on_release(s)
        self.assertEqual(callbacks["ctrl+s"], [1])

        hm.stop()
        self.assertFalse(hm.is_running())


if __name__ == "__main__":
    unittest.main()
