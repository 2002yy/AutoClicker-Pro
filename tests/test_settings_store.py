"""
settings_store 单元测试（密钥目录重定向到临时目录）
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings_store import load_settings, save_settings


class TestSettingsStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._patcher = patch('config.settings_store.os.path.expanduser',
                              return_value=self.tmp)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_roundtrip(self):
        data = {'hotkeys': {'toggle': 'f7', 'panic': 'esc'}}
        self.assertTrue(save_settings(data))
        self.assertEqual(load_settings(), data)

    def test_load_missing_returns_empty(self):
        self.assertEqual(load_settings(), {})

    def test_load_corrupted_returns_empty(self):
        settings_dir = os.path.join(self.tmp, '.autoclicker_pro')
        os.makedirs(settings_dir, exist_ok=True)
        with open(os.path.join(settings_dir, 'settings.json'), 'w') as f:
            f.write('{not json')
        self.assertEqual(load_settings(), {})

    def test_load_non_dict_returns_empty(self):
        settings_dir = os.path.join(self.tmp, '.autoclicker_pro')
        os.makedirs(settings_dir, exist_ok=True)
        with open(os.path.join(settings_dir, 'settings.json'), 'w') as f:
            json.dump([1, 2], f)
        self.assertEqual(load_settings(), {})


if __name__ == '__main__':
    unittest.main()
