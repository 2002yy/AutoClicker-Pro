"""
GUI 冒烟测试

背景：v2.0.x 曾因 StatusBar 使用未导入的常量导致启动即 NameError 崩溃，
而 62 项纯逻辑单测全部通过——回归直达用户。本文件保证"应用能实例化、
能完成一次布局计算、能干净退出"，在 CI 的 Windows job 中随单测一起执行。
"""

import gc
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tkinter as tk


def _teardown_root(root):
    """统一清理：先在 Tcl 环境存活时回收 Tk 包装对象（StringVar 等），
    再销毁根窗口——避免残留对象在解释器退出期跨线程回收触发
    Tcl_AsyncDelete 硬崩溃"""
    gc.collect()
    try:
        root.destroy()
    except tk.TclError:
        pass


def _root_or_skip(testcase):
    """创建 Tk 根窗口；无显示环境（如部分 CI 容器）则跳过"""
    try:
        root = tk.Tk()
    except tk.TclError as e:
        testcase.skipTest(f"无可用显示环境：{e}")
        raise  # skipTest 必然抛出，这里仅为类型检查明确控制流
    root.withdraw()
    return root


class TestStatusBar(unittest.TestCase):
    """直接覆盖启动崩溃回归点（COLOR_DISABLED 未导入）"""

    def test_instantiate_and_set_status(self):
        from ui.components.status_bar import StatusBar
        root = _root_or_skip(self)
        try:
            bar = StatusBar(root)
            root.update()
            bar.set_recording()
            self.assertEqual(bar.status_label.cget("text"), "正在录制鼠标/键盘... 按 ESC 停止")
            bar.set_error("boom")
            self.assertIn("boom", bar.status_label.cget("text"))
            bar.set_encryption_notice(False)
            bar.set_encryption_notice(True)
        finally:
            _teardown_root(root)

    def test_all_status_colors_exist(self):
        import ui.components.status_bar as sb
        for name in ("COLOR_DARK", "COLOR_DANGER", "COLOR_SUCCESS",
                     "COLOR_WARNING", "COLOR_DISABLED"):
            self.assertTrue(hasattr(sb, name), f"status_bar 缺少常量 {name}")


class TestAppSmoke(unittest.TestCase):
    """完整应用冒烟：实例化 -> 布局 -> 队列泵 -> 干净退出"""

    def setUp(self):
        self.root = _root_or_skip(self)

    def tearDown(self):
        _teardown_root(self.root)

    def test_app_boots_and_layouts(self):
        from ui.app import AutoClickerApp
        app = AutoClickerApp(self.root)

        # 关键组件就位
        for attr in ("settings_panel", "control_buttons", "action_list",
                     "status_bar", "engine"):
            self.assertTrue(hasattr(app, attr), f"缺少组件 {attr}")

        # 强制一轮完整布局计算（会执行所有待布局回调，捕获创建期异常）
        self.root.update()

        # 引擎钩子已接线
        self.assertIsNotNone(app.engine.ignore_click_predicate)
        self.assertIsNotNone(app.engine.on_status_change)

        # 初始按钮状态：无动作时点击/保存禁用
        self.assertEqual(str(app.control_buttons.click_button.cget("state")), "disabled")
        self.assertEqual(str(app.control_buttons.save_button.cget("state")), "disabled")

        app.on_close()

    def test_ui_queue_dispatches_on_main_thread(self):
        from ui.app import AutoClickerApp
        app = AutoClickerApp(self.root)
        seen = []
        app._dispatch_to_ui(lambda: seen.append(1))
        app._dispatch_to_ui(lambda: seen.append(2))
        app._drain_ui_queue()  # 同步消费一轮，行为确定
        self.assertEqual(seen, [1, 2])
        # 关闭后不应再接受投递
        app.on_close()
        app._dispatch_to_ui(lambda: seen.append(3))
        self.assertEqual(seen, [1, 2])

    def test_window_bounds_tracking(self):
        from ui.app import AutoClickerApp
        app = AutoClickerApp(self.root)
        self.root.geometry("400x550+50+50")
        self.root.update()
        app._refresh_window_bounds()
        left, top, right, bottom = app._window_bounds
        self.assertLessEqual(left, 50)      # 含边框，不大于客户区 x
        self.assertLessEqual(top, 50)       # 含标题栏
        self.assertGreater(right - left, 0)
        self.assertGreater(bottom - top, 0)
        # 窗口内的点应被判定为 True（录制过滤的基础）
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        self.assertTrue(app._is_point_in_own_window(cx, cy))
        self.assertFalse(app._is_point_in_own_window(left + right + 10, cy))
        app.on_close()


def _fill_hotkeys(panel, **overrides):
    """把四个快捷键字段填成互不冲突的默认值，再套用覆盖项"""
    values = {'toggle': 'f8', 'start_recording': 'f10',
              'stop_recording': 'f11', 'panic': 'esc'}
    values.update(overrides)
    panel.set_values(values)


class TestHotkeySettingsPanel(unittest.TestCase):
    """快捷键自定义面板：校验与错误提示"""

    def setUp(self):
        self.root = _root_or_skip(self)
        from ui.components.hotkey_settings import HotkeySettings
        self.panel = HotkeySettings(self.root, on_apply=lambda v: None)

    def tearDown(self):
        _teardown_root(self.root)

    def test_valid_single_keys_pass(self):
        _fill_hotkeys(self.panel)
        ok, msg = self.panel.validate()
        self.assertTrue(ok, msg)

    def test_valid_combo_key_passes(self):
        _fill_hotkeys(self.panel, toggle='ctrl+shift+f9')
        ok, msg = self.panel.validate()
        self.assertTrue(ok, msg)

    def test_rejects_empty(self):
        _fill_hotkeys(self.panel, panic='')
        ok, msg = self.panel.validate()
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)

    def test_rejects_unknown_key_name(self):
        _fill_hotkeys(self.panel, toggle='notakey')
        ok, msg = self.panel.validate()
        self.assertFalse(ok)
        self.assertIn("无效", msg)

    def test_rejects_duplicates(self):
        _fill_hotkeys(self.panel, start_recording='f8')
        ok, msg = self.panel.validate()
        self.assertFalse(ok)
        self.assertIn("重复", msg)


class TestApplyAndEditFlow(unittest.TestCase):
    """应用自定义快捷键 + 动作列表编辑的端到端流程"""

    def setUp(self):
        self.root = _root_or_skip(self)

    def tearDown(self):
        _teardown_root(self.root)

    @staticmethod
    def _make_app(root):
        from unittest.mock import patch
        with patch('ui.app.save_settings', return_value=True) as save_mock:
            from ui.app import AutoClickerApp
            app = AutoClickerApp(root)
        return app, save_mock

    def test_apply_hotkeys_updates_state_and_persists(self):
        from unittest.mock import patch
        app, save_mock = self._make_app(self.root)
        try:
            app.hotkey_settings.set_values({
                'toggle': 'f7', 'start_recording': 'f10',
                'stop_recording': 'f11', 'panic': 'esc'})
            with patch('ui.app.save_settings', return_value=True) as save2:
                app._apply_hotkeys(app.hotkey_settings.get_values())

            self.assertEqual(app.hotkeys['toggle'], 'f7')
            self.assertIn('F7', app.hotkey_hint_label.cget('text'))
            # 新的启停键不再被录进宏
            self.assertIn('f7', app.engine.get_skip_key_names())
            self.assertTrue(save2.called)
            self.assertIn("已更新", app.status_bar.status_label.cget("text"))

            # 非法输入：保持原快捷键并显示错误，不触发保存
            app.hotkey_settings.set_values({
                'toggle': 'x1', 'start_recording': 'x1',
                'stop_recording': 'f11', 'panic': 'esc'})
            with patch('ui.app.save_settings', return_value=True) as save3:
                app._apply_hotkeys(app.hotkey_settings.get_values())
            self.assertEqual(app.hotkeys['toggle'], 'f7')  # 未被破坏
            self.assertFalse(save3.called)
            self.assertTrue(app.hotkey_settings.error_label is not None)
        finally:
            app.on_close()

    def test_action_edit_flow(self):
        from core.macros import ClickAction
        app, _ = self._make_app(self.root)
        try:
            app.engine.click_sequence = [
                ClickAction(1, 1, 'left', 'press', 0.0),
                ClickAction(2, 2, 'left', 'press', 0.1),
                ClickAction(3, 3, 'left', 'press', 0.2),
            ]
            app._refresh_actions_ui()
            self.assertEqual(app.action_list.get_count(), 3)

            # 删除中间动作，列表与引擎同步
            app.action_list.select_index(1)
            app._on_delete_action()
            self.assertEqual([a.x for a in app.engine.get_sequence()], [1, 3])
            self.assertEqual(app.action_list.get_count(), 2)

            # 下移末位无效（按钮边界），上移有效且保持选中
            app.action_list.select_index(1)
            app._on_move_action(1)
            self.assertEqual([a.x for a in app.engine.get_sequence()], [1, 3])
            app._on_move_action(-1)
            self.assertEqual([a.x for a in app.engine.get_sequence()], [3, 1])
            self.assertEqual(app.action_list.get_selected_index(), 0)

            # 清空（经 UI 队列回调刷新）
            app._on_clear_actions()
            app._drain_ui_queue()
            self.assertEqual(len(app.engine.get_sequence()), 0)
            self.assertEqual(app.action_list.get_count(), 0)
            self.assertEqual(str(app.action_list.clear_button.cget("state")),
                             "disabled")
            self.assertEqual(str(app.control_buttons.click_button.cget("state")),
                             "disabled")
        finally:
            app.on_close()


class TestTrajectoryFolding(unittest.TestCase):
    """连续移动轨迹的折叠显示与区间编辑"""

    def setUp(self):
        self.root = _root_or_skip(self)

    def tearDown(self):
        _teardown_root(self.root)

    @staticmethod
    def _drag_sequence():
        from core.macros import ClickAction
        return [
            ClickAction(10, 10, 'left', 'press', 0.0),
            ClickAction(20, 20, '', 'move', 0.05, kind='move'),
            ClickAction(30, 30, '', 'move', 0.08, kind='move'),
            ClickAction(40, 40, '', 'move', 0.11, kind='move'),
            ClickAction(40, 40, 'left', 'release', 0.15),
        ]

    def test_folding_maps_rows_to_ranges(self):
        app, _ = TestApplyAndEditFlow._make_app(self.root)
        try:
            app.engine.click_sequence = self._drag_sequence()
            app._refresh_actions_ui()
            # 折叠后 3 行：press / 轨迹×3 / release
            self.assertEqual(app.action_list.get_count(), 3)
            self.assertEqual(app.action_list.get_row_range(0), (0, 0))
            self.assertEqual(app.action_list.get_row_range(1), (1, 3))
            self.assertEqual(app.action_list.get_row_range(2), (4, 4))
            self.assertTrue(app.action_list.is_folded_row(1))
            self.assertFalse(app.action_list.is_folded_row(0))
            row_text = app.action_list.listbox.get(1)
            self.assertIn('拖拽轨迹', row_text)
            self.assertIn('×3', row_text)
        finally:
            app.on_close()

    def test_delete_folded_row_removes_whole_run(self):
        app, _ = TestApplyAndEditFlow._make_app(self.root)
        try:
            app.engine.click_sequence = self._drag_sequence()
            app._refresh_actions_ui()
            app.action_list.select_index(1)      # 轨迹行
            app._on_delete_action()
            remaining = [a.kind for a in app.engine.get_sequence()]
            self.assertEqual(remaining, ['mouse', 'mouse'])  # press+release
        finally:
            app.on_close()

    def test_move_on_folded_row_rejected_with_hint(self):
        app, _ = TestApplyAndEditFlow._make_app(self.root)
        try:
            app.engine.click_sequence = self._drag_sequence()
            app._refresh_actions_ui()
            app.action_list.select_index(1)
            app._on_move_action(-1)
            unchanged = [a.kind for a in app.engine.get_sequence()]
            self.assertEqual(unchanged,
                             ['mouse', 'move', 'move', 'move', 'mouse'])
            self.assertIn("不支持整体移动",
                          app.status_bar.status_label.cget("text"))
            # 上移按钮应处于禁用态（选中折叠行时）
            state = str(app.action_list.move_up_button.cget("state"))
            self.assertEqual(state, "disabled")
        finally:
            app.on_close()


class TestMacroLibraryFlow(unittest.TestCase):
    """宏库端到端：保存入库 / 加载 / 删除（库目录重定向到临时目录）"""

    def setUp(self):
        import shutil
        import tempfile
        from unittest.mock import patch
        self.tmp = tempfile.mkdtemp()
        self._expand_patcher = patch(
            'config.macro_library.os.path.expanduser', return_value=self.tmp)
        self._expand_patcher.start()

        self.root = _root_or_skip(self)
        self.app, _ = TestApplyAndEditFlow._make_app(self.root)
        self.shutil = shutil

    def tearDown(self):
        try:
            self.app.on_close()
        except Exception:
            pass
        _teardown_root(self.root)
        self._expand_patcher.stop()
        self.shutil.rmtree(self.tmp, ignore_errors=True)

    def _inject_sequence(self):
        from core.macros import ClickAction
        self.app.engine.click_sequence = [
            ClickAction(1, 1, 'left', 'press', 0.0),
            ClickAction(2, 2, 'left', 'release', 0.1),
        ]
        self.app._refresh_actions_ui()

    def test_save_to_library_and_load_back(self):
        from unittest.mock import patch
        from config.constants import STATUS_ENCRYPTION_NOTICE
        self._inject_sequence()

        with patch('ui.app.simpledialog.askstring', return_value='登录流程'):
            with patch('config.macro_library.os.path.expanduser',
                       return_value=self.tmp):
                self.app._on_save_click()

        # 下拉框已刷新并选中（展示文本含元数据，真实名经映射还原）
        self.assertEqual(self.app.library_panel.get_selected(), '登录流程')
        displays = list(self.app.library_panel.combo['values'])
        self.assertTrue(any(d.startswith('登录流程') for d in displays),
                        displays)
        self.assertTrue(any('2 个动作' in d for d in displays), displays)
        self.assertIn('已保存到宏库',
                      self.app.status_bar.status_label.cget("text"))

        # 清空后从库加载回来
        self.app.engine.clear_sequence()
        self.app._drain_ui_queue()
        with patch('config.macro_library.os.path.expanduser',
                   return_value=self.tmp):
            self.app._on_library_load('登录流程')
        loaded = self.app.engine.get_sequence()
        self.assertEqual([(a.x, a.y) for a in loaded], [(1, 1), (2, 2)])

    def test_save_cancelled_does_not_write(self):
        from unittest.mock import patch
        self._inject_sequence()
        with patch('ui.app.simpledialog.askstring', return_value=None):
            with patch('config.macro_library.os.path.expanduser',
                       return_value=self.tmp):
                self.app._on_save_click()
        self.assertFalse(self.app.library_panel.combo['values'])
        self.assertIsNone(self.app.library_panel.get_selected())

    def test_delete_requires_confirm(self):
        from unittest.mock import patch
        from config import macro_library
        self._inject_sequence()
        with patch('ui.app.simpledialog.askstring', return_value='tmp宏'):
            self.app._on_save_click()  # expanduser 已在 setUp 打补丁
        self.assertIn('tmp宏', macro_library.list_macros())

        # 拒绝确认 -> 不删除
        with patch('ui.app.messagebox.askyesno', return_value=False):
            self.app._on_library_delete('tmp宏')
        self.assertIn('tmp宏', macro_library.list_macros())

        # 确认 -> 删除且下拉刷新
        with patch('ui.app.messagebox.askyesno', return_value=True):
            self.app._on_library_delete('tmp宏')
        self.assertNotIn('tmp宏', macro_library.list_macros())
        self.assertIsNone(self.app.library_panel.get_selected())


class TestCoordinateEditing(unittest.TestCase):
    """坐标微调：按钮状态门控与写回"""

    def setUp(self):
        self.root = _root_or_skip(self)

    def tearDown(self):
        _teardown_root(self.root)

    def test_edit_coordinates_updates_action(self):
        from core.macros import ClickAction
        from unittest.mock import patch
        app, _ = TestApplyAndEditFlow._make_app(self.root)
        try:
            app.engine.click_sequence = [
                ClickAction(10, 20, 'left', 'press', 0.0),
                ClickAction(30, 40, 'left', 'release', 0.1),
            ]
            app._refresh_actions_ui()

            # 鼠标动作行 -> 坐标编辑按钮可用
            app.action_list.select_index(0)
            state = str(app.action_list.edit_button.cget("state"))
            self.assertEqual(state, "normal")

            # 键盘动作行 -> 不可用
            app.engine.click_sequence.append(
                ClickAction(0, 0, '', 'press', 0.2, kind='key', key='a'))
            app._refresh_actions_ui()
            app.action_list.select_index(2)
            self.assertEqual(str(app.action_list.edit_button.cget("state")),
                             "disabled")

            # 折叠轨迹行 -> 不可用
            app.engine.click_sequence = [
                ClickAction(1, 1, 'left', 'press', 0.0),
                ClickAction(5, 5, '', 'move', 0.05, kind='move'),
                ClickAction(6, 6, '', 'move', 0.08, kind='move'),
            ]
            app._refresh_actions_ui()
            app.action_list.select_index(1)
            self.assertEqual(str(app.action_list.edit_button.cget("state")),
                             "disabled")

            # 打桩对话框：模拟用户确认输入
            with patch.object(app, '_show_coord_dialog',
                              return_value=(777, 888)):
                app.action_list.select_index(0)
                app._on_edit_coords()
            action = app.engine.get_action(0)
            self.assertEqual((action.x, action.y), (777, 888))

            # 取消（返回 None）不改动
            with patch.object(app, '_show_coord_dialog', return_value=None):
                app._on_edit_coords()
            action = app.engine.get_action(0)
            self.assertEqual((action.x, action.y), (777, 888))
        finally:
            app.on_close()


class TestPanelPersistence(unittest.TestCase):
    """面板数值经 settings.json 跨会话持久化"""

    def setUp(self):
        import shutil as _sh
        import tempfile
        from unittest.mock import patch as _patch
        self._shutil = _sh
        self.tmp = tempfile.mkdtemp()
        self._expand_patcher = _patch(
            'config.macro_library.os.path.expanduser', return_value=self.tmp)
        self._expand_patcher.start()
        self.root = _root_or_skip(self)
        self.app, _ = TestApplyAndEditFlow._make_app(self.root)

    def tearDown(self):
        try:
            self.app.on_close()
        except Exception:
            pass
        _teardown_root(self.root)
        self._expand_patcher.stop()
        self._shutil.rmtree(self.tmp, ignore_errors=True)

    def test_panel_values_persist_across_sessions(self):
        """面板数值经 _update_engine_config 写入 settings.json，新实例恢复"""
        # 修改参数并触发保存
        self.app.settings_panel.set_values({'interval_ms': 250,
                                            'repeat_count': 7,
                                            'auto_stop_s': 90})
        self.app._update_engine_config()
        self.assertEqual(self.app.engine.interval_ms, 250)

        # 新实例（同一临时目录）应恢复这些值
        app2, _ = TestApplyAndEditFlow._make_app(self.root)
        try:
            self.assertEqual(app2.settings_panel.get_value('interval_ms'), 250)
            self.assertEqual(app2.settings_panel.get_value('repeat_count'), 7)
            self.assertEqual(app2.settings_panel.get_value('auto_stop_s'), 90)
            # 未保存过的字段保持默认
            self.assertEqual(app2.settings_panel.get_value('hold_duration'),
                             100)
        finally:
            app2.on_close()


if __name__ == "__main__":
    unittest.main()
