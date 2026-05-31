"""
键鼠输入模拟模块 - 使用 pynput 模拟键盘按键和鼠标点击
"""

import time
from typing import Optional, Tuple

from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

from config import config


class InputSimulator:
    """键盘 + 鼠标输入模拟器"""

    def __init__(self):
        self._keyboard = KeyboardController()
        self._mouse = MouseController()

    # ── 键盘 ──

    def press_key(self, key: str, duration: Optional[float] = None) -> None:
        """按下并释放按键。key 如 'F', 'A', 'D', 'E'"""
        duration = duration or config.button_press_duration
        self._keyboard.press(key)
        time.sleep(duration)
        self._keyboard.release(key)

    def tap(self, key: str) -> None:
        """快速点按"""
        self.press_key(key)

    # ── 鼠标 ──

    def move_to(self, x: int, y: int) -> None:
        """移动鼠标到屏幕绝对坐标"""
        self._mouse.position = (x, y)
        time.sleep(0.01)

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """鼠标左键点击。可先移动到 (x,y) 再点击"""
        if x is not None and y is not None:
            self.move_to(x, y)
        self._mouse.click(Button.left)
        time.sleep(0.05)

    def click_at(self, position: Tuple[int, int]) -> None:
        """在指定位置点击"""
        self.click(position[0], position[1])

    # ── 复位 ──

    def reset(self) -> None:
        """释放所有按键（pynput 自动处理）"""
        pass

    def idle(self, seconds: float = 0.1) -> None:
        """短暂空闲等待"""
        time.sleep(seconds)

    def __del__(self):
        self.reset()
