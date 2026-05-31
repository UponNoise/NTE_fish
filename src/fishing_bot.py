"""
钓鱼机器人主逻辑 - 串联屏幕捕获、图像识别、键鼠模拟和状态机

流程:
  START → INIT_SETUP → CAST → WAIT_BITE → HOOK → REELING → COLLECT → CHECK_BAIT
       ↑                                                                     ↓
       └──────────────────────────────← (bait OK) ←──────────────────────────┘
                                              ↓ (bait low)
                                         SELL_BUY (占位)
"""

import time
import threading
from typing import Optional, Tuple

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
        self.input.set_focus_callback(self.capture.focus_game_window)
        self.state_machine = FishingStateMachine()

        self._thread: Optional[threading.Thread] = None
        self._bite_start_time: float = 0.0
        self._hook_start_time: float = 0.0
        self._last_f_press: float = 0.0      # 上次按 F 的时间戳
        self._reel_start_time: float = 0.0

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

    def _click_capture_position(self, position: tuple[int, int], label: str = "") -> None:
        x, y = self.capture.to_screen_position(position)
        self.input.click(x, y)
        if label:
            self._log(f"{label} ({x},{y})")

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
        if config.use_window_capture:
            if self.capture.focus_game_window():
                self._log("已切换到游戏窗口")
            else:
                self._log("[警告] 无法自动切到游戏窗口，请手动点一下游戏窗口")
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
        self.state_machine.state = FishState.START
        self._log("跳过准备界面识别，直接开始钓鱼流程")

        while not self.state_machine.should_stop():
            try:
                screenshot = self.capture.capture()
                current = self.state_machine.state
                recog = self._recognize_scene(screenshot, current)
                next_state = self.state_machine.next_state(recog)

                if next_state == FishState.STOPPED:
                    break

                if next_state != current:
                    self._execute_entry(next_state, screenshot, recog)
                    self.state_machine.state = next_state

                active_state = self.state_machine.state
                self._execute_continuous(active_state, screenshot, recog)
                self._check_timeouts(active_state)
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

    def _recognize_scene(self, screenshot: np.ndarray, state: FishState) -> dict:
        """按当前状态做最少量识别，避免每帧扫描全部模板。"""
        recog: dict = {}

        if state == FishState.WAIT_BITE:
            reeling = self.recognizer.detect_reeling(screenshot)
            recog["has_bite"] = self.recognizer.detect_bite(screenshot)
            recog["is_reeling"] = reeling is not None
            recog["reeling"] = reeling
        elif state == FishState.HOOK:
            reeling = self.recognizer.detect_reeling(screenshot)
            recog["is_reeling"] = reeling is not None
            recog["reeling"] = reeling
        elif state == FishState.REELING:
            reeling = self.recognizer.detect_reeling(screenshot)
            recog["is_reeling"] = reeling is not None
            recog["reeling"] = reeling
            if reeling is None and time.time() - self._reel_start_time > 2.0:
                # 遛鱼 UI 消失且已遛鱼超过 2s → 进入轮询等待 catch 结果
                polled = self._poll_catch_result()
                if polled is not None:
                    recog["reel_result"] = polled[0]
                    recog["catch_position"] = (polled[1], polled[2])
        elif state == FishState.CHECK_BAIT:
            recog["bait_low"] = self.recognizer.detect_bait_low(screenshot)

        return recog

    def _detect_reel_result(self, screenshot: np.ndarray) -> Optional[Tuple[str, int, int]]:
        """单帧检测 catch 结果，返回 (结果名, x, y) 或 None。"""
        r = self.recognizer.detect_catch_result(screenshot, threshold=0.55)
        if r is None:
            return None
        name = r[0]
        result = "success" if "success" in name else "fail"
        return (result, r[1], r[2])

    def _poll_catch_result(self, max_attempts: int = 40, interval: float = 0.12) -> Optional[Tuple[str, int, int]]:
        """遛鱼结束后轮询检测 catch 结果，容忍过渡动画延迟。

        最多轮询 max_attempts 次（约 4.8 秒），在游戏过渡动画期间持续尝试。
        返回 (结果名, click_x, click_y) 或 None。
        """
        for i in range(max_attempts):
            ss = self.capture.capture()
            r = self.recognizer.detect_catch_result(ss, threshold=0.55)
            if r is not None:
                name = r[0]
                result = "success" if "success" in name else "fail"
                self._log(f"轮询第 {i+1} 次检测到结果: {result} @ ({r[1]},{r[2]})")
                return (result, r[1], r[2])
            time.sleep(interval)
        return None

    # ── 状态入口动作 ──

    def _execute_entry(self, state: FishState, screenshot: np.ndarray, recog: dict):
        self._log(f">>> 进入 {state.name}")

        if state == FishState.INIT_SETUP:
            self._do_initial_setup(screenshot)

        elif state == FishState.CAST:
            time.sleep(config.cast_animation_wait)
            self.input.tap("F")
            self._log("按 F 抛竿")

        elif state == FishState.WAIT_BITE:
            self._bite_start_time = time.time()
            self._last_f_press = time.time()
            self._log(f"开始定时按 F（间隔 {config.bite_f_interval}s）...")

        elif state == FishState.HOOK:
            self._hook_start_time = time.time()
            time.sleep(config.hook_animation_wait)
            self.input.tap("F")
            self._log("按 F 起勾")

        elif state == FishState.REELING:
            self._reel_start_time = time.time()
            self._log("遛鱼中 (A/D)...")

        elif state == FishState.COLLECT:
            self._do_collect(screenshot, recog)

        elif state == FishState.CHECK_BAIT:
            self._log("检查鱼饵...")

        elif state == FishState.SELL_BUY:
            self._do_sell_buy()

    # ── 持续动作 ──

    def _execute_continuous(self, state: FishState, screenshot: np.ndarray, recog: dict):
        if state == FishState.WAIT_BITE:
            # 定时按 F 直到遛鱼界面出现
            now = time.time()
            if now - self._last_f_press >= config.bite_f_interval:
                self.input.tap("F")
                self._last_f_press = now
        elif state == FishState.REELING:
            info = recog.get("reeling") or self.recognizer.detect_reeling(screenshot)
            if info and info.get("action") not in (None, "NONE"):
                self.input.press_key(info["action"], config.reel_press_duration)

    # ── 超时检查 ──

    def _check_timeouts(self, state: FishState):
        if state == FishState.WAIT_BITE:
            if time.time() - self._bite_start_time > config.bite_timeout:
                self._log("等待上钩超时，重新抛竿")
                self._execute_entry(FishState.CAST, self.capture.capture(), {})
                self.state_machine.state = FishState.CAST
        elif state == FishState.REELING:
            if time.time() - self._reel_start_time > config.reel_timeout:
                # 超时前最后尝试检测 catch 结果（可能模板匹配阈值刚好差一点）
                ss = self.capture.capture()
                result_tuple = self._detect_reel_result(ss)
                if result_tuple:
                    result_name, cx, cy = result_tuple
                    self._log(f"遛鱼超时但检测到结果: {result_name} @ ({cx},{cy})")
                    recog_dict = {"reel_result": result_name, "catch_position": (cx, cy)}
                    if self.state_machine.next_state(recog_dict) == FishState.COLLECT:
                        self._execute_entry(FishState.COLLECT, ss, recog_dict)
                        self.state_machine.state = FishState.COLLECT
                        return
                self._log("遛鱼超时，鱼可能跑了")
                self.state_machine._cycle_count += 1
                self._execute_entry(FishState.CAST, self.capture.capture(), {})
                self.state_machine.state = FishState.CAST
        elif state == FishState.HOOK:
            if time.time() - self._hook_start_time > 5.0:
                self._log("起勾后未进入遛鱼，回到等待")
                self._bite_start_time = time.time()
                self._last_f_press = time.time()
                self.state_machine.state = FishState.WAIT_BITE

    # ── 子流程 ──

    def _do_initial_setup(self, screenshot: np.ndarray):
        """首次准备：E 换鱼饵 → 检测 bait + exchange → 点击确认。"""
        self._log("首次准备：按 E 打开换鱼饵界面...")
        self.input.tap("E")
        time.sleep(2.0)

        # exchange_bait 模板可能较大难以匹配，优先检测 bait 和 exchange 两个小元素
        for attempt in range(15):
            ss = self.capture.capture()
            ui = self.recognizer.detect_bait_exchange_ui(ss)

            # 成功: 同时检测到 bait 和 exchange
            if ui.get("bait") and ui.get("exchange"):
                self._log(f"检测到换饵界面 bait=({ui['bait'][0]},{ui['bait'][1]}) exchange=({ui['exchange'][0]},{ui['exchange'][1]})")
                self._click_capture_position(ui["bait"], "点击鱼饵")
                time.sleep(1.0)
                self._click_capture_position(ui["exchange"], "点击确认更换")
                time.sleep(2.0)
                return

            # 降级: 只检测到 exchange → 可能已在界面内，直接点击
            if ui.get("exchange"):
                self._log(f"仅检测到 exchange，直接点击 ({ui['exchange'][0]},{ui['exchange'][1]})")
                self._click_capture_position(ui["exchange"], "点击确认更换")
                time.sleep(1.5)
                return

            # 降级: 只检测到 bait → 点击后等 exchange 出现
            if ui.get("bait"):
                self._log(f"仅检测到 bait，点击 ({ui['bait'][0]},{ui['bait'][1]})")
                self._click_capture_position(ui["bait"], "点击鱼饵")
                time.sleep(1.0)
                # 再试检测 exchange
                ss2 = self.capture.capture()
                ui2 = self.recognizer.detect_bait_exchange_ui(ss2)
                if ui2.get("exchange"):
                    self._click_capture_position(ui2["exchange"], "点击确认更换")
                    time.sleep(1.5)
                    return

            time.sleep(0.5)

        self._log("[提示] 未识别到换鱼饵界面，跳过换饵并继续抛竿")

    def _do_collect(self, screenshot: np.ndarray, recog: dict = None):
        """点击收杆结果。

        优先使用 _poll_catch_result 传来的缓存坐标（最准确），
        未命中时才用当前截图重新检测。
        """
        recog = recog or {}
        cached = recog.get("catch_position")
        if cached is not None:
            self._click_capture_position(cached, "点击收杆结果（缓存坐标）")
            time.sleep(1.0)
            return

        # 缓存未命中，重新检测
        r = self.recognizer.detect_catch_result(screenshot, threshold=0.55)
        if r:
            _, cx, cy = r
            self._click_capture_position((cx, cy), "点击收杆结果（实时检测）")
            time.sleep(1.0)
        else:
            self._log("[警告] 未找到收杆结果，跳过点击")

    def _do_sell_buy(self):
        """尝试处理出售/返回钓鱼相关界面。"""
        self._log("尝试处理出售/购买界面...")

        clicked_any = False
        for _ in range(10):
            ss = self.capture.capture()
            ui = self.recognizer.detect_sell_buy_ui(ss)

            for key, label in (
                ("quick_submit", "点击快捷提交"),
                ("sell_all", "点击一键出售"),
                ("confirm", "点击确认"),
                ("go_fishing", "点击前往钓鱼"),
                ("close", "关闭弹窗"),
            ):
                position = ui.get(key)
                if position:
                    self._click_capture_position(position, label)
                    clicked_any = True
                    time.sleep(1.0)
                    break
            else:
                time.sleep(0.4)
                continue

        if not clicked_any:
            self._log("[提示] 未识别到出售/购买按钮，跳过该步骤")

