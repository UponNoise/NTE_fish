"""
钓鱼机器人主逻辑 - 串联屏幕捕获、图像识别、键鼠模拟和状态机

流程:
  CHECK_READY → INIT_SETUP → CAST → WAIT_BITE → HOOK → REELING → COLLECT → CHECK_BAIT
       ↑                                                                     ↓
       └──────────────────────────────← (bait OK) ←──────────────────────────┘
                                              ↓ (bait low)
                                         SELL_BUY (占位)
"""

import time
import threading
from typing import Optional

import numpy as np

from config import config
from src.screen_capture import ScreenCapture
from src.image_recognizer import ImageRecognizer
from src.input_simulator import InputSimulator
from src.state_machine import FishingStateMachine, FishState


class FishingBot:
    """异环钓鱼自动化机器人（键鼠版）"""

    def __init__(self):
        self.capture = ScreenCapture(
            region=config.capture_region,
            use_window=config.use_window_capture,
            process_name=config.target_process,
        )
        self.recognizer = ImageRecognizer()
        self.input = InputSimulator()
        self.state_machine = FishingStateMachine()

        self._thread: Optional[threading.Thread] = None
        self._bite_start_time: float = 0.0
        self._reel_start_time: float = 0.0
        self._check_ready_timeout: float = 0.0  # CHECK_READY 阶段超时用

        # 回调
        self.state_machine.set_on_state_change(self._on_state_changed)
        self.state_machine.set_on_log(self._on_bot_log)

    # ── 外部回调 ──

    def set_on_log(self, cb):          self._on_user_log = cb
    def set_on_state_change(self, cb): self._on_user_state_change = cb
    def set_on_fish_caught(self, cb):  self.state_machine.set_on_fish_caught(cb)
    def set_on_stopped(self, cb):      self._on_user_stopped = cb

    def _on_bot_log(self, msg: str):
        if hasattr(self, "_on_user_log") and self._on_user_log:
            self._on_user_log(msg)

    def _on_state_changed(self, old: FishState, new: FishState):
        self._log(f"[状态] {old.name} → {new.name}")
        if hasattr(self, "_on_user_state_change") and self._on_user_state_change:
            self._on_user_state_change(old, new)

    def _log(self, msg: str):
        self._on_bot_log(msg)

    # ── 窗口检测 ──

    def find_game_window(self) -> Optional[dict]:
        region = self.capture.find_game_window()
        if region is None:
            return None
        return {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}

    # ── 启动/停止 ──

    def start(self):
        if self._thread and self._thread.is_alive():
            self._log("机器人已在运行中")
            return
        self.state_machine.reset()
        self._log("=" * 50)
        self._log("钓鱼机器人启动（键鼠模式）")
        self._log("=" * 50)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._log("正在停止...")
        self.state_machine.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._log("机器人已停止")

    # ── 主循环 ──

    def _run_loop(self):
        self.state_machine.state = FishState.CHECK_READY
        self._check_ready_timeout = time.time()

        while not self.state_machine.should_stop():
            try:
                screenshot = self.capture.capture()
                recog = self._recognize_scene(screenshot)
                current = self.state_machine.state
                next_state = self.state_machine.next_state(recog)

                if next_state == FishState.STOPPED:
                    break

                if next_state != current:
                    self._execute_entry(next_state, screenshot, recog)
                    self.state_machine.state = next_state

                self._execute_continuous(current, screenshot, recog)
                self._check_timeouts(current)
                time.sleep(config.screen_capture_interval)

            except Exception as e:
                self._log(f"[错误] {e}")
                import traceback
                self._log(traceback.format_exc())
                time.sleep(0.5)

        self.state_machine.state = FishState.STOPPED
        if hasattr(self, "_on_user_stopped") and self._on_user_stopped:
            self._on_user_stopped()

    # ── 场景识别 ──

    def _recognize_scene(self, screenshot: np.ndarray) -> dict:
        return {
            "has_ef_ui": self.recognizer.detect_bottom_right_ui(screenshot) is not None,
            "has_bite": self.recognizer.is_present(screenshot, "bite_indicator"),
            "is_reeling": self.recognizer.is_present(screenshot, "green_zone"),
            "reel_result": self._detect_reel_result(screenshot),
            "bait_low": self.recognizer.is_present(screenshot, "bait_low_warning"),
            "setup_complete": False,  # 由 _execute_entry 中设置
        }

    def _detect_reel_result(self, screenshot: np.ndarray) -> Optional[str]:
        r = self.recognizer.detect_catch_result(screenshot)
        if r is None:
            return None
        name = r[0]
        return "success" if "success" in name else "fail"

    # ── 状态入口动作 ──

    def _execute_entry(self, state: FishState, screenshot: np.ndarray, recog: dict):
        self._log(f">>> 进入 {state.name}")

        if state == FishState.CHECK_READY:
            self._check_ready_timeout = time.time()

        elif state == FishState.INIT_SETUP:
            self._do_initial_setup(screenshot)

        elif state == FishState.CAST:
            time.sleep(config.cast_animation_wait)
            self.input.tap("F")
            self._log("按 F 抛竿")

        elif state == FishState.WAIT_BITE:
            self._bite_start_time = time.time()
            self._log("等待鱼上钩...")

        elif state == FishState.HOOK:
            time.sleep(config.hook_animation_wait)
            self.input.tap("F")
            self._log("按 F 起勾")

        elif state == FishState.REELING:
            self._reel_start_time = time.time()
            self._log("遛鱼中 (A/D)...")

        elif state == FishState.COLLECT:
            self._do_collect(screenshot)

        elif state == FishState.CHECK_BAIT:
            self._log("检查鱼饵...")

        elif state == FishState.SELL_BUY:
            self._log("[SELL_BUY] 暂留空，返回钓鱼循环")

    # ── 持续动作 ──

    def _execute_continuous(self, state: FishState, screenshot: np.ndarray, recog: dict):
        if state == FishState.REELING:
            info = self.recognizer.detect_reeling(screenshot)
            if info and info.get("action") not in (None, "NONE"):
                self.input.tap(info["action"])

    # ── 超时检查 ──

    def _check_timeouts(self, state: FishState):
        if state == FishState.CHECK_READY:
            if time.time() - self._check_ready_timeout > config.ready_timeout:
                self._log("[中断] 未检测到钓鱼准备界面，请进入钓鱼准备界面后重试")
                self.state_machine.stop()
        elif state == FishState.WAIT_BITE:
            if time.time() - self._bite_start_time > config.bite_timeout:
                self._log("等待上钩超时，重新抛竿")
                self.state_machine.state = FishState.CAST
        elif state == FishState.REELING:
            if time.time() - self._reel_start_time > config.reel_timeout:
                self._log("遛鱼超时，鱼可能跑了")
                self.state_machine._cycle_count += 1
                self.state_machine.state = FishState.CAST

    # ── 子流程 ──

    def _do_initial_setup(self, screenshot: np.ndarray):
        """首次准备：E → 换鱼饵界面 → 点击 bait → 点击 exchange"""
        self._log("首次准备：按 E 打开换鱼饵界面...")
        self.input.tap("E")
        time.sleep(1.5)

        # 等待识别 exchange_bait
        for attempt in range(8):
            ss = self.capture.capture()
            ui = self.recognizer.detect_bait_exchange_ui(ss)
            if ui.get("exchange_bait"):
                self._log("检测到换鱼饵界面")

                # 点击 bait
                if ui.get("bait"):
                    self.input.click_at(ui["bait"])
                    self._log("点击鱼饵")
                    time.sleep(0.8)

                # 点击 exchange
                if ui.get("exchange"):
                    self.input.click_at(ui["exchange"])
                    self._log("点击确认更换")
                    time.sleep(1.5)

                # 标记完成
                recog = self._recognize_scene(self.capture.capture())
                recog["setup_complete"] = True
                self.state_machine.next_state(recog)
                return

            # 若 exchange_bait 还没出现但 exchange 单独出现 → 可能已经在界面内
            if ui.get("exchange"):
                self.input.click_at(ui["exchange"])
                self._log("直接点击 exchange")
                time.sleep(1.5)
                recog = self._recognize_scene(self.capture.capture())
                recog["setup_complete"] = True
                self.state_machine.next_state(recog)
                return

            time.sleep(0.5)

        self._log("[警告] 换鱼饵界面识别超时，跳过")
        # 仍然标记完成以便继续
        recog = self._recognize_scene(self.capture.capture())
        recog["setup_complete"] = True

    def _do_collect(self, screenshot: np.ndarray):
        """点击收杆结果"""
        r = self.recognizer.detect_catch_result(screenshot)
        if r:
            _, cx, cy = r
            self.input.click(cx, cy)
            self._log(f"点击收杆结果 ({cx},{cy})")
            time.sleep(1.0)
        else:
            self._log("[警告] 未找到收杆结果，跳过点击")

