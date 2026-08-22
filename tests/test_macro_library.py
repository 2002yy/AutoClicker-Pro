"""
宏库管理单元测试（库目录重定向到临时目录）
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import macro_library

_ACTIONS = [{'x': 1, 'y': 2, 'button': 'left', 'action_type': 'press'}]


class TestMacroLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patcher = patch('config.macro_library.os.path.expanduser',
                              return_value=self.tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_list_load_roundtrip(self):
        used = macro_library.save_to_library('登录流程', _ACTIONS)
        self.assertEqual(used, '登录流程')
        self.assertIn('登录流程', macro_library.list_macros())
        loaded = macro_library.load_from_library('登录流程')
        self.assertEqual(loaded, _ACTIONS)

    def test_sanitize_strips_invalid_chars(self):
        self.assertEqual(macro_library.sanitize_name('a<b>:"/\\|?*c'), 'abc')
        self.assertEqual(macro_library.sanitize_name('  名字  '), '名字')
        self.assertEqual(macro_library.sanitize_name('..'), '')
        self.assertEqual(macro_library.sanitize_name('trailing.'), 'trailing')

    def test_save_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            macro_library.save_to_library('///', _ACTIONS)

    def test_delete_macro(self):
        macro_library.save_to_library('tmp', _ACTIONS)
        self.assertTrue(macro_library.delete_macro('tmp'))
        self.assertNotIn('tmp', macro_library.list_macros())
        self.assertFalse(macro_library.delete_macro('tmp'))  # 再删返回 False

    def test_load_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            macro_library.load_from_library('不存在')

    def test_overwrite_updates_content(self):
        macro_library.save_to_library('m', _ACTIONS)
        new_actions = [{'x': 9, 'y': 9, 'button': 'right', 'action_type': 'press'}]
        macro_library.save_to_library('m', new_actions)
        self.assertEqual(macro_library.load_from_library('m'), new_actions)
        self.assertEqual(macro_library.list_macros().count('m'), 1)

    def test_meta_reports_action_count_and_time(self):
        import datetime
        macro_library.save_to_library('meta宏', _ACTIONS * 3)
        meta = macro_library.get_macro_meta('meta宏')
        self.assertEqual(meta['actions'], 3)
        self.assertIsInstance(meta['mtime'], datetime.datetime)

        items = macro_library.list_macros_with_meta()
        entry = next(m for m in items if m['name'] == 'meta宏')
        display = macro_library.format_macro_display(entry)
        self.assertTrue(display.startswith('meta宏'))
        self.assertIn('3 个动作', display)
        self.assertIn('保存于', display)

    def test_meta_corrupt_file_still_listed(self):
        macro_library.save_to_library('bad', _ACTIONS)
        with open(macro_library._macro_path('bad'), 'w') as f:
            f.write('garbage-not-encrypted')
        meta = macro_library.get_macro_meta('bad')
        self.assertIsNone(meta['actions'])
        display = macro_library.format_macro_display(
            {'name': 'bad', 'actions': None, 'mtime': meta['mtime']})
        self.assertIn('无法读取', display)


if __name__ == '__main__':
    unittest.main()
