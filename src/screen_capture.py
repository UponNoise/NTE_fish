"""
屏幕捕获模块 - 使用 mss 进行快速屏幕截图
支持全屏捕获和指定进程窗口捕获两种模式
"""

import time
from typing import Tuple, Optional

import mss
import numpy as np

from config import config

try:
    from src.window_capture import WindowCapture
    HAS_WINDOW_CAPTURE = True
except ImportError:
    HAS_WINDOW_CAPTURE = False


class ScreenCapture:
    """屏幕捕获器，封装 mss 库，支持窗口/全屏双模式"""

    def __init__(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        use_window: bool = True,
        process_name: str = "HTGame.exe",
    ):
        """
        Args:
            region: 手动捕获区域 (left, top, width, height)，None 为全屏
            use_window: 是否启用窗口捕获模式
            process_name: 窗口捕获模式下的目标进程名
        """
        self._sct = mss.mss()
        self.region = region
        self.use_window = use_window
        self.process_name = process_name
        self._window_capture: Optional[WindowCapture] = None
        self._last_origin: Tuple[int, int] = (0, 0)

        if use_window and HAS_WINDOW_CAPTURE:
            self._window_capture = WindowCapture(process_name)

    def capture(self) -> np.ndarray:
        """截取当前屏幕，返回 BGR 格式的 numpy 数组 (H, W, 3)"""
        # 优先使用窗口捕获
        if self.use_window and self._window_capture is not None:
            region = self._window_capture.get_capture_region()
            if region is not None:
                self._last_origin = (region[0], region[1])
                img = self._window_capture.capture_region(self._sct, region)
                if img is not None:
                    return img

            img = self._window_capture.capture_window(self._sct)
            if img is not None:
                return img

        # 回退到手动区域或全屏
        if self.region:
            self._last_origin = (self.region[0], self.region[1])
            monitor = {
                "left": self.region[0],
                "top": self.region[1],
                "width": self.region[2],
                "height": self.region[3],
            }
        else:
            monitor = self._sct.monitors[1]
            self._last_origin = (monitor.get("left", 0), monitor.get("top", 0))

        sct_img = self._sct.grab(monitor)
        img = np.array(sct_img, dtype=np.uint8)
        return img[:, :, :3]

    def to_screen_position(self, position: Tuple[int, int]) -> Tuple[int, int]:
        """把截图内坐标转换成屏幕绝对坐标。"""
        return (self._last_origin[0] + int(position[0]), self._last_origin[1] + int(position[1]))

    def capture_bgr(self) -> np.ndarray:
        """同 capture()，显式返回 BGR"""
        return self.capture()

    def set_region(self, region: Optional[Tuple[int, int, int, int]]):
        """动态设置手动捕获区域"""
        self.region = region

    def set_window_mode(self, enabled: bool, process_name: str = "HTGame.exe"):
        """启用/禁用窗口捕获模式"""
        self.use_window = enabled
        self.process_name = process_name
        if enabled and HAS_WINDOW_CAPTURE:
            if self._window_capture is None:
                self._window_capture = WindowCapture(process_name)
            else:
                self._window_capture.process_name = process_name.lower()
        elif not enabled:
            self._window_capture = None

    def find_game_window(self) -> Optional[Tuple[int, int, int, int]]:
        """查找游戏窗口，返回 (left, top, width, height) 或 None"""
        if not HAS_WINDOW_CAPTURE:
            return None
        wc = self._window_capture or WindowCapture(self.process_name)
        hwnd = wc.find_window()
        if hwnd is None:
            return None
        return wc.get_capture_region()

    def focus_game_window(self) -> bool:
        """尝试把目标游戏窗口置前。"""
        if not HAS_WINDOW_CAPTURE:
            return False
        wc = self._window_capture or WindowCapture(self.process_name)
        return wc.focus_window()

    @property
    def window_capture(self) -> Optional[WindowCapture]:
        return self._window_capture

    @property
    def monitors(self):
        """返回所有显示器信息"""
        return self._sct.monitors

    def __del__(self):
        if hasattr(self, "_sct") and self._sct:
            self._sct.close()
