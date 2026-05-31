"""
窗口捕获模块 - 定位并捕获指定进程的游戏窗口
仅支持 Windows（使用 win32gui）
"""

import ctypes
import time
from ctypes import wintypes
from typing import Optional, Tuple, List

import numpy as np

try:
    import win32gui
    import win32process
    import win32con
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


# 分辨率约束
RESOLUTION_MIN = (800, 600)       # 最小 800×600
RESOLUTION_MAX = (3840, 2160)     # 最大 3840×2160


class WindowCapture:
    """定位并捕获指定进程的窗口画面"""

    def __init__(self, process_name: str = "HTGame.exe"):
        """
        Args:
            process_name: 目标进程名（如 HTGame.exe）
        """
        self.process_name = process_name.lower()
        self._hwnd: Optional[int] = None
        self._last_rect: Optional[Tuple[int, int, int, int]] = None

    # ---- 窗口查找 ----

    def find_window(self) -> Optional[int]:
        """查找目标进程的主窗口句柄，返回 hwnd 或 None"""
        if not HAS_WIN32:
            raise RuntimeError("需要 pywin32 和 psutil：pip install pywin32 psutil")

        self._hwnd = None
        target_pids = self._find_process_pids(self.process_name)

        if not target_pids:
            return None

        def _enum_callback(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in target_pids:
                # 取最大的可见窗口（通常是主窗口）
                rect = win32gui.GetWindowRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
                existing = getattr(_enum_callback, "best", None)
                if existing is None or w * h > existing[1]:
                    _enum_callback.best = (hwnd, w * h)
            return True

        _enum_callback.best = None
        win32gui.EnumWindows(_enum_callback, None)

        if _enum_callback.best:
            self._hwnd = _enum_callback.best[0]
        return self._hwnd

    @staticmethod
    def _find_process_pids(name: str) -> set:
        """根据进程名查找所有 PID"""
        pids = set()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == name:
                    pids.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids

    def is_window_alive(self) -> bool:
        """检查之前找到的窗口是否仍然存在"""
        if self._hwnd is None:
            return False
        try:
            return win32gui.IsWindow(self._hwnd)
        except Exception:
            return False

    def focus_window(self) -> bool:
        """尽量把目标窗口切到前台，便于游戏接收 SendInput 按键。"""
        if not HAS_WIN32:
            return False

        if self._hwnd is None:
            hwnd = self.find_window()
            if hwnd is None:
                return False
        else:
            hwnd = self._hwnd

        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
            user32.AttachThreadInput.restype = wintypes.BOOL
            user32.GetForegroundWindow.restype = wintypes.HWND
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD

            foreground = user32.GetForegroundWindow()
            current_thread = kernel32.GetCurrentThreadId()
            foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground)
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

            if foreground_thread != current_thread:
                user32.AttachThreadInput(current_thread, foreground_thread, True)
            if target_thread != current_thread:
                user32.AttachThreadInput(current_thread, target_thread, True)

            try:
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            finally:
                if target_thread != current_thread:
                    user32.AttachThreadInput(current_thread, target_thread, False)
                if foreground_thread != current_thread:
                    user32.AttachThreadInput(current_thread, foreground_thread, False)

            time.sleep(0.1)
            return user32.GetForegroundWindow() == hwnd
        except Exception:
            return False

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        获取目标窗口的客户区矩形。

        Returns:
            (left, top, right, bottom) 或 None
        """
        if self._hwnd is None:
            hwnd = self.find_window()
            if hwnd is None:
                return None
        try:
            rect = win32gui.GetClientRect(self._hwnd)
            pt = win32gui.ClientToScreen(self._hwnd, (rect[0], rect[1]))
            result = (pt[0], pt[1], pt[0] + rect[2] - rect[0], pt[1] + rect[3] - rect[1])
            self._last_rect = result
            return result
        except Exception:
            self._hwnd = None
            return None

    def get_capture_region(self) -> Optional[Tuple[int, int, int, int]]:
        """
        获取 mss 格式的捕获区域。

        Returns:
            (left, top, width, height) 或 None
        """
        rect = self.get_window_rect()
        if rect is None:
            return None
        left, top, right, bottom = rect
        w, h = right - left, bottom - top

        # 分辨率合法性校验
        if w < RESOLUTION_MIN[0] or h < RESOLUTION_MIN[1]:
            return None  # 窗口太小，可能是最小化
        if w > RESOLUTION_MAX[0] or h > RESOLUTION_MAX[1]:
            # 超出上限时裁剪到上限（适配 4K）
            w = min(w, RESOLUTION_MAX[0])
            h = min(h, RESOLUTION_MAX[1])

        return (left, top, w, h)

    # ---- 截屏 ----

    def capture_window(self, sct) -> Optional[np.ndarray]:
        """
        使用已有的 mss 实例截取窗口画面。

        Args:
            sct: mss.mss() 实例

        Returns:
            BGR numpy 数组 (H, W, 3) 或 None
        """
        region = self.get_capture_region()
        if region is None:
            return None
        monitor = {
            "left": region[0],
            "top": region[1],
            "width": region[2],
            "height": region[3],
        }
        try:
            sct_img = sct.grab(monitor)
            img = np.array(sct_img, dtype=np.uint8)
            return img[:, :, :3]
        except Exception:
            return None

    # ---- 静态工具 ----

    @staticmethod
    def validate_resolution(width: int, height: int) -> Tuple[int, int]:
        """
        校验并修正分辨率到合法范围。

        Returns:
            (clamped_width, clamped_height)
        """
        w = max(RESOLUTION_MIN[0], min(width, RESOLUTION_MAX[0]))
        h = max(RESOLUTION_MIN[1], min(height, RESOLUTION_MAX[1]))
        return (w, h)

    @staticmethod
    def list_game_windows(process_name: str = "HTGame.exe") -> List[dict]:
        """列出所有目标进程的可见窗口（供 GUI 使用）"""
        if not HAS_WIN32:
            return []

        pids = WindowCapture._find_process_pids(process_name.lower())
        if not pids:
            return []

        results = []
        def _enum(hwnd, _extra):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in pids:
                rect = win32gui.GetWindowRect(hwnd)
                title = win32gui.GetWindowText(hwnd)
                results.append({
                    "hwnd": hwnd,
                    "title": title,
                    "rect": rect,
                    "size": f"{rect[2]-rect[0]}×{rect[3]-rect[1]}",
                })
            return True

        win32gui.EnumWindows(_enum, None)
        return results
