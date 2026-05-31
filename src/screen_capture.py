"""
屏幕捕获模块 - 使用 mss 进行快速屏幕截图
"""

import time
from typing import Tuple, Optional

import mss
import numpy as np


class ScreenCapture:
    """屏幕捕获器，封装 mss 库"""

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        Args:
            region: 捕获区域 (left, top, width, height)，None 为全屏
        """
        self._sct = mss.mss()
        self.region = region  # (left, top, width, height)

    def capture(self) -> np.ndarray:
        """截取当前屏幕，返回 BGR 格式的 numpy 数组 (H, W, 3)"""
        if self.region:
            monitor = {
                "left": self.region[0],
                "top": self.region[1],
                "width": self.region[2],
                "height": self.region[3],
            }
        else:
            monitor = self._sct.monitors[1]  # 主显示器

        sct_img = self._sct.grab(monitor)
        # mss 返回 BGRA，转为 numpy BGR 数组
        img = np.array(sct_img, dtype=np.uint8)
        return img[:, :, :3]  # 去掉 alpha 通道

    def capture_bgr(self) -> np.ndarray:
        """同 capture()，显式返回 BGR"""
        return self.capture()

    def set_region(self, region: Optional[Tuple[int, int, int, int]]):
        """动态设置捕获区域"""
        self.region = region

    @property
    def monitors(self):
        """返回所有显示器信息"""
        return self._sct.monitors

    def __del__(self):
        if hasattr(self, "_sct") and self._sct:
            self._sct.close()
