"""
设置持久化模块

把应用级设置（当前仅自定义快捷键）保存为
~/.autoclicker_pro/settings.json（明文 JSON，不含任何敏感数据）。
读取失败一律返回空字典并回退默认值，绝不阻断启动。
"""

import json
import os
from typing import Any, Dict

from .constants import CONFIG_DIR

SETTINGS_FILE = "settings.json"


def _settings_path() -> str:
    """settings.json 的绝对路径"""
    return os.path.join(os.path.expanduser("~"), CONFIG_DIR, SETTINGS_FILE)


def load_settings() -> Dict[str, Any]:
    """加载设置；文件缺失/损坏时返回空字典"""
    try:
        with open(_settings_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    保存设置（整体覆盖写入）

    Returns:
        是否成功
    """
    path = _settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
