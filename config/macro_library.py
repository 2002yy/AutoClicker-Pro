"""
宏库管理模块

宏库存放于 ~/.autoclicker_pro/macros/ 下的 .enc 文件（与导入/导出格式一致）。
提供按名称的保存 / 加载 / 删除 / 列举，名称即文件名主干。
"""

import os
import re
from typing import List

from .constants import CONFIG_DIR
from .encryption import encrypt_macro, decrypt_macro

MACROS_DIR = "macros"

# Windows 文件名非法字符与控制字符
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def library_dir() -> str:
    """宏库目录（确保存在）"""
    path = os.path.join(os.path.expanduser("~"), CONFIG_DIR, MACROS_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def sanitize_name(name: str) -> str:
    """清洗宏名：去除路径分隔符与非法字符、首尾空白；仅剩空白返回空串"""
    cleaned = _INVALID_NAME_CHARS.sub('', str(name)).strip().rstrip('.')
    return cleaned


def _macro_path(name: str) -> str:
    return os.path.join(library_dir(), f"{name}.enc")


def list_macros() -> List[str]:
    """列举宏库中的宏名（按名称排序，无扩展名）"""
    try:
        entries = os.listdir(library_dir())
    except OSError:
        return []
    names = [e[:-4] for e in entries
             if e.lower().endswith('.enc')
             and os.path.isfile(os.path.join(library_dir(), e))]
    return sorted(names)


def macro_exists(name: str) -> bool:
    return os.path.isfile(_macro_path(name))


def save_to_library(name: str, actions_data: list) -> str:
    """加密保存动作列表到宏库，返回实际使用的宏名"""
    clean = sanitize_name(name)
    if not clean:
        raise ValueError("宏名称不能为空")
    path = _macro_path(clean)
    encrypt_macro(actions_data, path)
    return clean


def load_from_library(name: str) -> list:
    """从宏库加载并解密动作列表；不存在抛 FileNotFoundError"""
    if not macro_exists(name):
        raise FileNotFoundError(f"宏不存在：{name}")
    return decrypt_macro(_macro_path(name))


def delete_macro(name: str) -> bool:
    """删除宏库中的宏；返回是否发生了删除"""
    try:
        os.remove(_macro_path(name))
        return True
    except OSError:
        return False
