"""
手柄输入模拟模块 - 使用 vgamepad 模拟 Xbox 360 手柄
"""

import time
import threading
from enum import Enum
from typing import Optional

import vgamepad as vg

from config import config


class GamepadButton(Enum):
    """Xbox 手柄按键映射"""
    A = "A"
    B = "B"
    X = "X"
    Y = "Y"
    LB = "LB"
    RB = "RB"
    LT = "LT"
    RT = "RT"
    START = "START"      # 菜单键
    BACK = "BACK"        # 视图键
    DPAD_UP = "DPAD_UP"
    DPAD_DOWN = "DPAD_DOWN"
    DPAD_LEFT = "DPAD_LEFT"
    DPAD_RIGHT = "DPAD_RIGHT"


class InputSimulator:
    """虚拟 Xbox 360 手柄输入模拟器"""

    def __init__(self):
        self._gamepad = vg.VX360Gamepad()

    def press_button(
        self,
        button: GamepadButton,
        duration: Optional[float] = None,
    ) -> None:
        """
        按下并释放一个按键。

        Args:
            button: 要按下的按键
            duration: 按下持续时间（秒），默认使用配置值
        """
        duration = duration or config.button_press_duration
        self._set_button(button, True)
        self._gamepad.update()
        time.sleep(duration)
        self._set_button(button, False)
        self._gamepad.update()

    def hold_button(self, button: GamepadButton) -> None:
        """按住按键（不释放）"""
        self._set_button(button, True)
        self._gamepad.update()

    def release_button(self, button: GamepadButton) -> None:
        """释放按键"""
        self._set_button(button, False)
        self._gamepad.update()

    def press_trigger(
        self,
        trigger: GamepadButton,
        value: float = 1.0,
        duration: Optional[float] = None,
    ) -> None:
        """
        按下扳机键（LT/RT）。

        Args:
            trigger: LT 或 RT
            value: 按下力度 0.0 ~ 1.0
            duration: 持续时间（秒）
        """
        if trigger not in (GamepadButton.LT, GamepadButton.RT):
            raise ValueError("扳机键仅支持 LT 或 RT")

        duration = duration or config.button_press_duration
        self._set_trigger(trigger, value)
        self._gamepad.update()
        time.sleep(duration)
        self._set_trigger(trigger, 0.0)
        self._gamepad.update()

    def tap_reel(self, direction: str, duration: Optional[float] = None) -> None:
        """
        轻触遛鱼方向键（用于微调浮标）。

        Args:
            direction: "LT" 或 "RT"
            duration: 按键时长，默认使用 reel_press_min
        """
        duration = duration or config.reel_press_min
        btn = GamepadButton.LT if direction.upper() == "LT" else GamepadButton.RT
        self.press_trigger(btn, value=1.0, duration=duration)

    def reset(self) -> None:
        """释放所有按键和扳机"""
        self._gamepad.reset()
        self._gamepad.update()

    def _set_button(self, button: GamepadButton, pressed: bool) -> None:
        """内部方法：设置按键状态"""
        mapping = {
            GamepadButton.A: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            GamepadButton.B: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            GamepadButton.X: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            GamepadButton.Y: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            GamepadButton.LB: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            GamepadButton.RB: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            GamepadButton.START: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            GamepadButton.BACK: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            GamepadButton.DPAD_UP: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            GamepadButton.DPAD_DOWN: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            GamepadButton.DPAD_LEFT: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            GamepadButton.DPAD_RIGHT: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }
        if button in mapping:
            if pressed:
                self._gamepad.press_button(button=mapping[button])
            else:
                self._gamepad.release_button(button=mapping[button])

    def _set_trigger(self, trigger: GamepadButton, value: float) -> None:
        """内部方法：设置扳机值"""
        val = int(max(0.0, min(1.0, value)) * 255)
        if trigger == GamepadButton.LT:
            self._gamepad.left_trigger_float(value_float=value)
        elif trigger == GamepadButton.RT:
            self._gamepad.right_trigger_float(value_float=value)

    def __del__(self):
        self.reset()
