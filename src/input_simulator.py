"""键鼠输入模拟模块 - 使用 Windows SendInput 模拟游戏可识别的输入。"""

import ctypes
import time
from ctypes import wintypes
from typing import Callable, Optional, Tuple

from config import config


ULONG_PTR = wintypes.WPARAM

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MAPVK_VK_TO_VSC = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001


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


class POINT(ctypes.Structure):
    _fields_ = (
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    )


SCAN_CODES = {
    "A": 0x1E,
    "D": 0x20,
    "E": 0x12,
    "F": 0x21,
}

VK_CODES = {
    "A": 0x41,
    "D": 0x44,
    "E": 0x45,
    "F": 0x46,
}


class InputSimulator:
    """键盘 + 鼠标输入模拟器"""

    def __init__(self):
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self._user32.SendInput.restype = wintypes.UINT
        self._user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
        self._user32.MapVirtualKeyW.restype = wintypes.UINT
        self._user32.keybd_event.argtypes = (wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ULONG_PTR)
        self._user32.keybd_event.restype = None
        self._user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self._user32.PostMessageW.restype = wintypes.BOOL
        self._user32.ScreenToClient.argtypes = (wintypes.HWND, ctypes.POINTER(POINT))
        self._user32.ScreenToClient.restype = wintypes.BOOL
        self._pressed_keys: set[str] = set()
        self._focus_callback: Optional[Callable[[], bool]] = None
        self._target_hwnd: Optional[int] = None

    def set_focus_callback(self, callback: Callable[[], bool]) -> None:
        """设置输入前的窗口聚焦回调。"""
        self._focus_callback = callback

    def set_target_hwnd(self, hwnd: Optional[int]) -> None:
        """设置后台输入目标窗口句柄。"""
        self._target_hwnd = hwnd

    def _use_post_message(self) -> bool:
        return config.input_backend.lower() == "post_message" and self._target_hwnd is not None

    # ── 键盘 ──

    def _focus_before_input(self) -> None:
        if self._use_post_message():
            return
        if config.auto_focus_input and self._focus_callback:
            self._focus_callback()
            time.sleep(0.03)

    def _send_input_keyboard(self, vk_code: int, scan_code: int, key_up: bool, use_scan_code: bool) -> None:
        flags = KEYEVENTF_KEYUP if key_up else 0
        w_vk = vk_code
        w_scan = scan_code
        if use_scan_code:
            flags |= KEYEVENTF_SCANCODE
            w_vk = 0

        data = INPUTUNION(ki=KEYBDINPUT(w_vk, w_scan, flags, 0, 0))
        event = INPUT(INPUT_KEYBOARD, data)
        sent = self._user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise OSError(error, f"SendInput keyboard failed for key {vk_code:#x}/{scan_code:#x}")

    def _send_keybd_event(self, vk_code: int, scan_code: int, key_up: bool) -> None:
        flags = KEYEVENTF_KEYUP if key_up else 0
        self._user32.keybd_event(vk_code, scan_code, flags, 0)

    def _scan_code_for(self, key: str) -> int:
        normalized = key.upper()
        if normalized not in SCAN_CODES:
            raise ValueError(f"不支持的按键: {key!r}，当前支持 {', '.join(sorted(SCAN_CODES))}")
        return SCAN_CODES[normalized]

    def _vk_code_for(self, key: str) -> int:
        normalized = key.upper()
        if normalized not in VK_CODES:
            raise ValueError(f"不支持的按键: {key!r}，当前支持 {', '.join(sorted(VK_CODES))}")
        return VK_CODES[normalized]

    def _post_key(self, vk_code: int, scan_code: int, key_up: bool) -> bool:
        hwnd = self._target_hwnd
        if hwnd is None:
            return False
        msg = WM_KEYUP if key_up else WM_KEYDOWN
        lparam = 1 | (scan_code << 16)
        if key_up:
            lparam |= 0xC0000000
        self._user32.PostMessageW(hwnd, msg, vk_code, lparam)
        return True

    def _send_key(self, key: str, key_up: bool = False) -> None:
        vk_code = self._vk_code_for(key)
        scan_code = self._scan_code_for(key)
        backend = config.input_backend.lower()

        if backend == "post_message":
            if self._post_key(vk_code, scan_code, key_up):
                return
            backend = "scan_code"

        if backend == "vk":
            mapped_scan = int(self._user32.MapVirtualKeyW(vk_code, MAPVK_VK_TO_VSC)) or scan_code
            self._send_input_keyboard(vk_code, mapped_scan, key_up, use_scan_code=False)
        elif backend == "keybd_event":
            self._send_keybd_event(vk_code, scan_code, key_up)
        else:
            self._send_input_keyboard(vk_code, scan_code, key_up, use_scan_code=True)

    def key_down(self, key: str) -> None:
        """按下按键。key 如 'F', 'A', 'D', 'E'"""
        normalized = key.upper()
        self._focus_before_input()
        self._send_key(normalized)
        self._pressed_keys.add(normalized)

    def key_up(self, key: str) -> None:
        """释放按键。key 如 'F', 'A', 'D', 'E'"""
        normalized = key.upper()
        self._send_key(normalized, key_up=True)
        self._pressed_keys.discard(normalized)

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
        self._focus_before_input()
        if self._use_post_message():
            return
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

    def _post_mouse_click(self, x: int, y: int) -> bool:
        hwnd = self._target_hwnd
        if hwnd is None:
            return False
        point = POINT(int(x), int(y))
        if not self._user32.ScreenToClient(hwnd, ctypes.byref(point)):
            return False
        lparam = (point.y << 16) | (point.x & 0xFFFF)
        self._user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        self._user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        self._user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
        return True

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """鼠标左键点击。可先移动到 (x,y) 再点击"""
        if x is not None and y is not None and self._use_post_message():
            if self._post_mouse_click(x, y):
                time.sleep(0.05)
                return

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
        for key in list(self._pressed_keys):
            try:
                self._send_key(key, key_up=True)
            finally:
                self._pressed_keys.discard(key)

    def idle(self, seconds: float = 0.1) -> None:
        """短暂空闲等待"""
        time.sleep(seconds)

    def __del__(self):
        self.reset()
