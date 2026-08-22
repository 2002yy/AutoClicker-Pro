"""
Win32 窗口查询模块

用 ctypes 直接调用 user32（无第三方依赖），为"窗口标题锚定"提供：
- get_foreground_window_info(): 前台窗口的标题与客户区矩形
- find_client_rect_by_title(): 按标题查找可见顶层窗口的客户区矩形

匹配策略：先精确匹配，失败后做大小写不敏感的"包含"匹配（浏览器等
应用标题尾部常带动态后缀）。全部找不到返回 None，由调用方降级处理。

非 Windows 平台所有函数返回 None/空，保证可导入、行为退化为绝对坐标。
"""

import sys
from typing import List, NamedTuple, Optional

IS_WINDOWS = sys.platform == 'win32'


class WindowRect(NamedTuple):
    """客户区在屏幕上的矩形（左上角原点）"""
    title: str
    left: int
    top: int
    right: int
    bottom: int


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32

    class _RECT(ctypes.Structure):
        _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                    ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

    class _POINT(ctypes.Structure):
        _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

    _EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _get_title(hwnd: int) -> str:
        length = _user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ''
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()

    def _get_client_rect(hwnd: int) -> Optional[WindowRect]:
        rect = _RECT()
        if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        origin = _POINT(0, 0)
        if not _user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            return None
        title = _get_title(hwnd)
        return WindowRect(title,
                          origin.x, origin.y,
                          origin.x + rect.right, origin.y + rect.bottom)

    def get_foreground_window_info() -> Optional[WindowRect]:
        """前台窗口信息；取不到（如无前台/权限受限）返回 None"""
        try:
            hwnd = _user32.GetForegroundWindow()
            if not hwnd:
                return None
            info = _get_client_rect(hwnd)
            if info and info.title:
                return info
            # 前台窗口拿不到标题时锚定无意义，按未捕获处理
            return None
        except Exception:
            return None

    def _enum_visible_windows() -> List[WindowRect]:
        results: List[WindowRect] = []

        @_EnumWindowsProc
        def _on_window(hwnd, _lparam):
            if _user32.IsWindowVisible(hwnd):
                info = _get_client_rect(hwnd)
                if info is not None and info.title:
                    results.append(info)
            return True

        try:
            _user32.EnumWindows(_on_window, 0)
        except Exception:
            pass
        return results

    def find_client_rect_by_title(title: str) -> Optional[WindowRect]:
        """按标题查找可见顶层窗口：先精确后包含（大小写不敏感）"""
        if not title:
            return None
        windows = _enum_visible_windows()

        target = title.casefold()
        for info in windows:
            if info.title == title:
                return info
        for info in windows:
            if target in info.title.casefold():
                return info
        return None

else:  # 非 Windows 占位实现

    def get_foreground_window_info() -> Optional[WindowRect]:
        return None

    def find_client_rect_by_title(title: str) -> Optional[WindowRect]:
        return None
