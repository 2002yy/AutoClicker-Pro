"""
文档截图生成工具（零第三方依赖）

在进程内启动应用并灌入演示数据，从屏幕 DC BitBlt 抓取窗口为 PNG，
输出到 docs/screenshots/，供 docs/TUTORIAL.md 使用。

首选屏幕 DC 抓取：能完整包含 ttk.Combobox 等原生子控件
（PrintWindow 会漏掉它们）。若显示器息屏/锁屏导致抓取为纯色，
自动回退 PrintWindow——自绘内容仍正确，仅原生子控件可能缺失。

用法：python tools/capture_docs_screens.py
"""

import ctypes
import os
import shutil
import sys
import tempfile
import time
import zlib
import struct
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# 截图脚本内禁用首启教程自动弹出（教程单独截一张）
os.environ["ACPRO_NO_TUTORIAL"] = "1"

OUT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
k32 = ctypes.windll.kernel32

# 防止自动化运行期间显示器息屏（黑屏截图的元凶）
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002


def _keep_awake(on: bool):
    flags = (_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED
             if on else _ES_CONTINUOUS)
    k32.SetThreadExecutionState(flags)


def _encode_png(width: int, height: int, topdown_bgra: bytes) -> bytes:
    """把 top-down BGRA 像素缓冲编码为 PNG（8bit RGB）"""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter: None
        row = topdown_bgra[y * stride:(y + 1) * stride]
        for x in range(width):
            off = x * 4
            raw += bytes((row[off + 2], row[off + 1], row[off]))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return (struct.pack(">I", len(payload)) + tag + payload +
                struct.pack(">I", crc))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def _is_uniform(mem_dc, w: int, h: int) -> bool:
    """粗查位图是否为单一纯色（锁屏/息屏时屏幕 DC 读数如此）"""
    pts = [(4, 4), (w // 2, 4), (w - 5, 4),
           (4, h // 2), (w // 2, h // 2), (w - 5, h // 2),
           (4, h - 5), (w // 2, h - 5), (w - 5, h - 5)]
    first = g32.GetPixel(mem_dc, *pts[0])
    return all(g32.GetPixel(mem_dc, x, y) == first for x, y in pts[1:])


def _visible_bounds(hwnd: int):
    """DWM 扩展边界（真实可见区域），剔除隐形缩放边框的桌面透底"""
    from ctypes import wintypes

    class RECT_(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    bounds = RECT_()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(bounds),
        ctypes.sizeof(bounds))
    return bounds


def _capture_window(hwnd: int):
    """按 DWM 可见边界从屏幕 DC 抓取窗口，返回 (png_bytes, (w, h))"""
    from ctypes import wintypes

    rect = _visible_bounds(hwnd)
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwnd_dc = u32.GetWindowDC(hwnd)
    mem_dc = g32.CreateCompatibleDC(hwnd_dc)
    bmp = g32.CreateCompatibleBitmap(hwnd_dc, w, h)
    old = g32.SelectObject(mem_dc, bmp)

    SRCCOPY = 0x00CC0020
    CAPTUREBLT = 0x40000000
    PW_RENDERFULLCONTENT = 2

    # 首选：屏幕 DC 抓取（能包含原生子控件）
    screen_dc = u32.GetDC(0)
    g32.BitBlt(mem_dc, 0, 0, w, h, screen_dc,
               rect.left, rect.top, SRCCOPY | CAPTUREBLT)
    u32.ReleaseDC(0, screen_dc)

    # 息屏/锁屏保护：纯色时回退 PrintWindow
    if _is_uniform(mem_dc, w, h):
        print("  [warn] 屏幕抓取为纯色（可能锁屏/息屏），回退 PrintWindow")
        u32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER)]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h          # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0      # BI_RGB

    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bmi), 0)

    png = _encode_png(w, h, buf.raw)

    g32.SelectObject(mem_dc, old)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mem_dc)
    u32.ReleaseDC(hwnd, hwnd_dc)
    return png, (w, h)


def _build_demo_app():
    """启动应用并灌入演示数据；返回 (root, app, cleanup)"""
    import tkinter as tk

    ctypes.windll.user32.SetProcessDPIAware()

    from ui.theme import apply_win11_theme
    from ui.app import AutoClickerApp
    from core.macros import ClickAction
    from config import macro_library

    # 库与加密全部重定向到临时目录，不污染真实用户目录
    tmp = tempfile.mkdtemp(prefix="acp_shots_")
    p1 = patch("config.macro_library.os.path.expanduser", return_value=tmp)
    p2 = patch("config.encryption.os.path.expanduser", return_value=tmp)
    p1.start()
    p2.start()

    # 预置两个演示宏，让宏库面板有内容可展示
    demo_click = [{"x": 640, "y": 400, "button": "left",
                   "action_type": "press"}]
    macro_library.save_to_library(
        "登录表单自动填写",
        demo_click + [{"kind": "key", "key": "tab", "action_type": "press"}])
    macro_library.save_to_library(
        "每日签到", [dict(demo_click[0])] * 5)

    root = tk.Tk()
    apply_win11_theme(root)
    app = AutoClickerApp(root)
    # 必须在 App 创建之后再设尺寸：_configure_window 会重置为 APP_WIDTH；
    # 加宽以保证宏库行（下拉框 + 四个按钮）完整展示
    root.geometry("800x1340+80+10")

    # 演示动作序列：锚定点击 -> 拖拽轨迹 -> Ctrl+C -> Enter
    title = "记事本.txt - 记事本"
    moves = [(128, 356), (150, 371), (176, 389), (196, 407)]
    seq = [
        ClickAction(120, 340, "left", "press", 0.00,
                    anchor_title=title, win_rel_x=120, win_rel_y=340),
    ]
    ts = 0.07
    for mx, my in moves:
        seq.append(ClickAction(mx, my, "", "move", round(ts, 2),
                               kind="move", anchor_title=title,
                               win_rel_x=mx, win_rel_y=my))
        ts += 0.09
    seq += [
        ClickAction(moves[-1][0], moves[-1][1], "left", "release", 0.43,
                    anchor_title=title,
                    win_rel_x=moves[-1][0], win_rel_y=moves[-1][1]),
        ClickAction(0, 0, "", "press", 0.62,
                    kind="chord", key="c", modifiers=["ctrl"]),
        ClickAction(0, 0, "", "press", 0.85, kind="key", key="enter"),
    ]
    app.engine.click_sequence = seq
    app._refresh_actions_ui()
    # 截图需要从第一条动作展示，抵消"录制时滚到底部"的效果
    root.update_idletasks()
    app.action_list.listbox.yview_moveto(0)

    return root, app, (p1, p2, tmp)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _keep_awake(True)

    root, app, cleanup = _build_demo_app()

    def shot(filename):
        root.update()
        time.sleep(0.25)
        root.update()
        hwnd = u32.GetParent(root.winfo_id()) or root.winfo_id()
        png, size = _capture_window(hwnd)
        out = OUT_DIR / filename
        out.write_bytes(png)
        print(f"{out} ({size[0]}x{size[1]}, {len(png)} bytes)")

    try:
        root.attributes("-topmost", True)
        root.update()

        # 截图一：主界面（已录制序列 + 宏库就绪）
        shot("main.png")

        # 截图二：录制中状态
        app.status_bar.set_recording()
        app.control_buttons.update_recording_state(True)
        shot("record-replay.png")

        # 截图三：新手教程弹窗（首启体验展示）
        from ui.components.tutorial_dialog import TutorialDialog
        dlg = TutorialDialog(root)
        root.update()
        time.sleep(0.25)
        root.update()
        hwnd = u32.GetParent(dlg.winfo_id()) or dlg.winfo_id()
        png, size = _capture_window(hwnd)
        out = OUT_DIR / "tutorial.png"
        out.write_bytes(png)
        print(f"{out} ({size[0]}x{size[1]}, {len(png)} bytes)")
        dlg.destroy()
    finally:
        _keep_awake(False)
        try:
            app.on_close()
        except Exception:
            pass
        _, _, tmp = cleanup
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
