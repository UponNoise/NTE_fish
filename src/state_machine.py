"""
钓鱼状态机 - 管理钓鱼自动化的全部状态流转

状态说明:
    CHECK_READY   - 检测右下角 E/F UI 是否存在，判断是否在钓鱼准备界面
    INIT_SETUP    - 首次准备：E 换鱼饵 → 点击 bait → 点击 exchange
    CAST          - 按 F 抛竿
    WAIT_BITE     - 等待鱼上钩（检测 bite_indicator）
    HOOK          - 按 F 起勾
    REELING       - A/D 遛鱼（保持 float_marker 重叠 green_zone）
    COLLECT       - 点击收杆结果 (catch_success / catch_fail)
    CHECK_BAIT    - 检查鱼饵是否不足 (bait_low_warning)
    SELL_BUY      - 出售渔获 + 购买鱼饵（暂留空）
    STOPPED       - 已停止
"""

import threading
from enum import Enum, auto
from typing import Optional, Callable

from config import config


class FishState(Enum):
    CHECK_READY = auto()
    INIT_SETUP = auto()
    CAST = auto()
    WAIT_BITE = auto()
    HOOK = auto()
    REELING = auto()
    COLLECT = auto()
    CHECK_BAIT = auto()
    SELL_BUY = auto()
    STOPPED = auto()


class FishingStateMachine:
    """钓鱼自动化状态机"""

    def __init__(self):
        self._state = FishState.CHECK_READY
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cycle_count: int = 0
        self._total_fish: int = 0
        self._initial_setup_done: bool = False

        # 回调
        self._on_state_change: Optional[Callable[[FishState, FishState], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_fish_caught: Optional[Callable[[int], None]] = None

    # ── 属性 ──

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
        return self.state not in (FishState.CHECK_READY, FishState.STOPPED)

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def total_fish(self) -> int:
        return self._total_fish

    # ── 回调 ──

    def set_on_state_change(self, cb):
        self._on_state_change = cb

    def set_on_log(self, cb):
        self._on_log = cb

    def set_on_fish_caught(self, cb):
        self._on_fish_caught = cb

    # ── 日志 ──

    def _log(self, msg: str):
        if self._on_log:
            self._on_log(msg)

    # ── 控制 ──

    def stop(self):
        self._stop_event.set()

    def reset(self):
        self._stop_event.clear()
        self._cycle_count = 0
        self._total_fish = 0
        self._initial_setup_done = False
        self.state = FishState.CHECK_READY

    def should_stop(self) -> bool:
        if self._stop_event.is_set():
            return True
        if config.max_cycles > 0 and self._cycle_count >= config.max_cycles:
            return True
        return False

    # ── 状态转换 ──

    def next_state(self, recog: dict) -> FishState:
        """
        根据当前状态和识别结果决定下一状态。

        recog 字典:
            has_ef_ui       : 右下角检测到 E/F 按键提示
            has_exchange_bait: 检测到换鱼饵界面
            has_bite        : 检测到鱼上钩
            is_reeling      : 检测到遛鱼界面 (green_zone + float_marker)
            reel_result     : "success" / "fail" / None
            bait_low        : 鱼饵不足警告
        """
        current = self.state

        if self.should_stop():
            return FishState.STOPPED

        # CHECK_READY → 有 E/F UI 则进入 INIT_SETUP，否则保持（外部超时中断）
        if current == FishState.CHECK_READY:
            if recog.get("has_ef_ui"):
                return FishState.INIT_SETUP if not self._initial_setup_done else FishState.CAST
            return FishState.CHECK_READY

        # INIT_SETUP → 完成换饵后 → CAST
        elif current == FishState.INIT_SETUP:
            if recog.get("setup_complete"):
                self._initial_setup_done = True
                return FishState.CAST
            return FishState.INIT_SETUP

        # CAST → 抛竿后进入等待
        elif current == FishState.CAST:
            return FishState.WAIT_BITE

        # WAIT_BITE → 有鱼上钩 → HOOK，否则继续等待
        elif current == FishState.WAIT_BITE:
            if recog.get("has_bite"):
                return FishState.HOOK
            return FishState.WAIT_BITE

        # HOOK → 出现遛鱼界面 → REELING
        elif current == FishState.HOOK:
            if recog.get("is_reeling"):
                return FishState.REELING
            return FishState.HOOK

        # REELING → 收杆结果 → COLLECT
        elif current == FishState.REELING:
            result = recog.get("reel_result")
            if result in ("success", "fail"):
                if result == "success":
                    self._total_fish += 1
                    if self._on_fish_caught:
                        self._on_fish_caught(self._total_fish)
                self._cycle_count += 1
                return FishState.COLLECT
            return FishState.REELING

        # COLLECT → 点击后检查鱼饵
        elif current == FishState.COLLECT:
            return FishState.CHECK_BAIT

        # CHECK_BAIT → 鱼饵不足 → SELL_BUY，否则 → CAST
        elif current == FishState.CHECK_BAIT:
            if recog.get("bait_low"):
                return FishState.SELL_BUY
            return FishState.CAST

        # SELL_BUY → 暂留空，直接回 CAST
        elif current == FishState.SELL_BUY:
            return FishState.CAST

        elif current == FishState.STOPPED:
            return FishState.STOPPED

        return current

