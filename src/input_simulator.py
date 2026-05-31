"""键鼠输入模拟模块 - 使用 Windows SendInput 模拟游戏可识别的输入。"""

import ctypes
import time
from ctypes import wintypes
from typing import Optional, Tuple

from config import config


ULONG_PTR = wintypes.WPARAM

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class INPUTUNION(ctypes.Union):
    _fields_ = (
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    )


class INPUT(ctypes.Structure):
    _fields_ = (
        ("type", wintypes.DWORD),
        ("union", INPUTUNION),
    )


SCAN_CODES = {
    "A": 0x1E,
    "D": 0x20,
    "E": 0x12,
    "F": 0x21,
}


class InputSimulator:
    """键盘 + 鼠标输入模拟器"""

    def __init__(self):
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self._user32.SendInput.restype = wintypes.UINT
        self._user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._pressed_scan_codes: set[int] = set()

    # ── 键盘 ──

    def _send_keyboard(self, scan_code: int, key_up: bool = False) -> None:
        flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
        data = INPUTUNION(ki=KEYBDINPUT(0, scan_code, flags, 0, 0))
        event = INPUT(INPUT_KEYBOARD, data)
        sent = self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, f"SendInput keyboard failed for scan code {scan_code:#x}")

    def _scan_code_for(self, key: str) -> int:
        normalized = key.upper()
        if normalized not in SCAN_CODES:
            raise ValueError(f"不支持的按键: {key!r}，当前支持 {', '.join(sorted(SCAN_CODES))}")
        return SCAN_CODES[normalized]

    def key_down(self, key: str) -> None:
        """按下按键。key 如 'F', 'A', 'D', 'E'"""
        scan_code = self._scan_code_for(key)
        self._send_keyboard(scan_code)
        self._pressed_scan_codes.add(scan_code)

    def key_up(self, key: str) -> None:
        """释放按键。key 如 'F', 'A', 'D', 'E'"""
        scan_code = self._scan_code_for(key)
        self._send_keyboard(scan_code, key_up=True)
        self._pressed_scan_codes.discard(scan_code)

    def press_key(self, key: str, duration: Optional[float] = None) -> None:
        """按下并释放按键。key 如 'F', 'A', 'D', 'E'"""
        duration = config.button_press_duration if duration is None else duration
        self.key_down(key)
        try:
            time.sleep(duration)
        finally:
            self.key_up(key)

    def tap(self, key: str) -> None:
        """快速点按"""
        self.press_key(key)

    # ── 鼠标 ──

    def move_to(self, x: int, y: int) -> None:
        """移动鼠标到屏幕绝对坐标"""
        if not self._user32.SetCursorPos(int(x), int(y)):
            error = ctypes.get_last_error()
            raise OSError(error, f"SetCursorPos failed at ({x}, {y})")
        time.sleep(0.01)

    def _send_mouse(self, flags: int) -> None:
        data = INPUTUNION(mi=MOUSEINPUT(0, 0, 0, flags, 0, 0))
        event = INPUT(INPUT_MOUSE, data)
        sent = self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, "SendInput mouse failed")

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """鼠标左键点击。可先移动到 (x,y) 再点击"""
        if x is not None and y is not None:
            self.move_to(x, y)
        self._send_mouse(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.03)
        self._send_mouse(MOUSEEVENTF_LEFTUP)
        time.sleep(0.05)

    def click_at(self, position: Tuple[int, int]) -> None:
        """在指定位置点击"""
        self.click(position[0], position[1])

    # ── 复位 ──

    def reset(self) -> None:
        """释放仍处于按下状态的按键。"""
        for scan_code in list(self._pressed_scan_codes):
            try:
                self._send_keyboard(scan_code, key_up=True)
            finally:
                self._pressed_scan_codes.discard(scan_code)

    def idle(self, seconds: float = 0.1) -> None:
        """短暂空闲等待"""
        time.sleep(seconds)

    def __del__(self):
        self.reset()
