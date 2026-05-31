"""
钓鱼状态机 - 管理钓鱼自动化的全部状态流转

状态说明:
    IDLE          - 空闲，未启动
    CASTING       - 按 A 抛竿
    WAITING_BITE  - 等待鱼上钩（检测屏幕）
    HOOKING       - 按 A 起勾
    REELING       - LT/RT 遛鱼（进度条平衡）
    CHECKING_BAIT - 检查鱼饵是否充足
    SELLING       - 按 X 进入渔获商店出售
    BUYING_BAIT   - 按菜单键进入商店购买鱼饵
    STOPPED       - 已停止
"""

import time
import threading
from enum import Enum, auto
from typing import Optional, Callable

from config import config


class FishState(Enum):
    IDLE = auto()
    CASTING = auto()
    WAITING_BITE = auto()
    HOOKING = auto()
    REELING = auto()
    CHECKING_BAIT = auto()
    SELLING = auto()
    BUYING_BAIT = auto()
    STOPPED = auto()


class FishingStateMachine:
    """钓鱼自动化状态机"""

    def __init__(self):
        self._state = FishState.IDLE
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cycle_count: int = 0
        self._total_fish: int = 0

        # 回调
        self._on_state_change: Optional[Callable[[FishState, FishState], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_fish_caught: Optional[Callable[[int], None]] = None

    # ---- 属性 ----

    @property
    def state(self) -> FishState:
        with self._lock:
            return self._state

    @state.setter
    def state(self, new_state: FishState):
        old = self.state
        with self._lock:
            self._state = new_state
        if self._on_state_change and old != new_state:
            self._on_state_change(old, new_state)

    @property
    def is_running(self) -> bool:
        return self.state not in (FishState.IDLE, FishState.STOPPED)

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def total_fish(self) -> int:
        return self._total_fish

    # ---- 回调设置 ----

    def set_on_state_change(self, cb: Callable[[FishState, FishState], None]):
        self._on_state_change = cb

    def set_on_log(self, cb: Callable[[str], None]):
        self._on_log = cb

    def set_on_fish_caught(self, cb: Callable[[int], None]):
        self._on_fish_caught = cb

    # ---- 日志 ----

    def _log(self, msg: str):
        if self._on_log:
            self._on_log(msg)

    def stop(self):
        """请求停止"""
        self._stop_event.set()

    def reset(self):
        """重置状态机"""
        self._stop_event.clear()
        self._cycle_count = 0
        self._total_fish = 0
        self.state = FishState.IDLE

    def should_stop(self) -> bool:
        """检查是否应停止"""
        if self._stop_event.is_set():
            return True
        if config.max_cycles > 0 and self._cycle_count >= config.max_cycles:
            return True
        return False

    # ---- 状态转换逻辑 ----

    def next_state(self, recognizer_result: dict) -> FishState:
        """
        根据当前状态和图像识别结果决定下一个状态。
        由外部（fishing_bot）调用。

        Args:
            recognizer_result: {
                "can_cast": bool,       # 检测到可抛竿状态
                "fish_bite": bool,      # 检测到鱼上钩
                "is_reeling": bool,     # 检测到遛鱼界面
                "bait_low": bool,       # 鱼饵不足
                "in_shop": bool,        # 在商店界面
                "in_sell": bool,        # 在出售界面
                "reel_done": bool,      # 遛鱼完成（鱼已上钩）
            }
        """
        current = self.state

        if self.should_stop():
            return FishState.STOPPED

        if current == FishState.IDLE:
            return FishState.CASTING

        elif current == FishState.CASTING:
            # 抛竿后等待动画，然后进入等待上钩
            return FishState.WAITING_BITE

        elif current == FishState.WAITING_BITE:
            if recognizer_result.get("fish_bite"):
                return FishState.HOOKING
            # 继续等待...（外部处理超时）
            return FishState.WAITING_BITE

        elif current == FishState.HOOKING:
            if recognizer_result.get("is_reeling"):
                return FishState.REELING
            # 起勾后短暂等待，再判断
            return FishState.HOOKING

        elif current == FishState.REELING:
            if recognizer_result.get("reel_done"):
                self._total_fish += 1
                if self._on_fish_caught:
                    self._on_fish_caught(self._total_fish)
                self._cycle_count += 1
                return FishState.CHECKING_BAIT
            return FishState.REELING

        elif current == FishState.CHECKING_BAIT:
            if recognizer_result.get("bait_low"):
                return FishState.SELLING
            else:
                return FishState.CASTING

        elif current == FishState.SELLING:
            if recognizer_result.get("in_sell"):
                # 还在出售界面，继续等待出售完成
                return FishState.SELLING
            else:
                # 出售完成，去买鱼饵
                return FishState.BUYING_BAIT

        elif current == FishState.BUYING_BAIT:
            if recognizer_result.get("in_shop"):
                return FishState.BUYING_BAIT
            else:
                # 购买完成，继续钓鱼
                return FishState.CASTING

        elif current == FishState.STOPPED:
            return FishState.STOPPED

        return current

    def get_state_actions(self, state: FishState) -> list[str]:
        """
        返回该状态下需要执行的操作序列。

        Returns:
            操作指令列表，如 ["A", "LT", "RT", "X", "B", "START", "WAIT_2s"]
        """
        actions = {
            FishState.IDLE: [],
            FishState.CASTING: ["A"],
            FishState.WAITING_BITE: [],  # 仅等待，无操作
            FishState.HOOKING: ["A"],
            FishState.REELING: [],       # 图像识别驱动 LT/RT
            FishState.CHECKING_BAIT: [],  # 仅检测，无操作
            FishState.SELLING: ["X"],     # 进入出售
            FishState.BUYING_BAIT: ["START"],  # 菜单键进入商店
        }
        return actions.get(state, [])
