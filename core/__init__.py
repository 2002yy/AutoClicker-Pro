"""核心模块包"""
# 注意：engine.py 需要 X server，在无头环境中导入会失败
# 只导出 macros 模块中的类以避免此问题
from .macros import ClickAction, MacroRecorder, MacroPlayer, MacroStorage

__all__ = ['ClickAction', 'MacroRecorder', 'MacroPlayer', 'MacroStorage']
