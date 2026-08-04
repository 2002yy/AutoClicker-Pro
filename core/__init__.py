"""核心模块包"""
# 注意：engine.py 依赖 pynput，在无图形环境中导入会失败，
# 因此这里只导出纯数据结构，需要引擎时请显式 from core.engine import ClickerEngine
from .macros import ClickAction

__all__ = ['ClickAction']
