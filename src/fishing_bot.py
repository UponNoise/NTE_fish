"""
钓鱼机器人主逻辑 - 串联屏幕捕获、图像识别、输入模拟和状态机
"""

import time
import threading
from typing import Optional

import numpy as np

from config import config
from src.screen_capture import ScreenCapture
from src.image_recognizer import ImageRecognizer, compute_reel_action
from src.input_simulator import InputSimulator, GamepadButton
from src.state_machine import FishingStateMachine, FishState


class FishingBot:
    """异环钓鱼自动化机器人"""

    def __init__(self):
        self.capture = ScreenCapture(region=config.capture_region)
        self.recognizer = ImageRecognizer()
        self.input = InputSimulator()
        self.state_machine = FishingStateMachine()

        self._thread: Optional[threading.Thread] = None
        self._bite_start_time: float = 0.0
        self._reel_start_time: float = 0.0

        # 设置状态机回调
        self.state_machine.set_on_state_change(self._on_state_changed)
        self.state_machine.set_on_log(self._on_bot_log)

    # ---- 外部回调（由 GUI 设置） ----

    def set_on_log(self, cb):
        self._on_user_log = cb

    def set_on_state_change(self, cb):
        self._on_user_state_change = cb

    def set_on_fish_caught(self, cb):
        self.state_machine.set_on_fish_caught(cb)

    def set_on_stopped(self, cb):
        self._on_user_stopped = cb

    def _on_bot_log(self, msg: str):
        if hasattr(self, "_on_user_log") and self._on_user_log:
            self._on_user_log(msg)

    def _on_state_changed(self, old: FishState, new: FishState):
        self._log(f"[状态] {old.name} → {new.name}")
        if hasattr(self, "_on_user_state_change") and self._on_user_state_change:
            self._on_user_state_change(old, new)

    def _log(self, msg: str):
        self._on_bot_log(msg)

    # ---- 启动/停止 ----

    def start(self):
        """启动钓鱼机器人"""
        if self._thread and self._thread.is_alive():
            self._log("机器人已在运行中")
            return

        self.state_machine.reset()
        self._log("=" * 50)
        self._log("钓鱼机器人启动")
        self._log(f"捕获间隔: {config.screen_capture_interval}s")
        self._log(f"匹配阈值: {config.match_threshold}")
        self._log("=" * 50)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止钓鱼机器人"""
        self._log("正在停止机器人...")
        self.state_machine.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.input.reset()
        self._log("机器人已停止")

    # ---- 主循环 ----

    def _run_loop(self):
        """主循环（在独立线程中运行）"""
        self.state_machine.state = FishState.CASTING

        while not self.state_machine.should_stop():
            try:
                # 1. 截屏
                screenshot = self.capture.capture()

                # 2. 识别当前场景
                recog = self._recognize_scene(screenshot)

                # 3. 状态机决定下一个状态
                current_state = self.state_machine.state
                next_state = self.state_machine.next_state(recog)

                if next_state == FishState.STOPPED:
                    break

                # 4. 状态变化时执行进入动作
                if next_state != current_state:
                    self.state_machine.state = next_state
                    self._execute_entry_actions(next_state, screenshot)

                # 5. 执行状态持续动作（如遛鱼）
                self._execute_continuous_actions(current_state, screenshot)

                # 6. 检查超时
                self._check_timeouts(current_state)

                # 7. 间隔等待
                time.sleep(config.screen_capture_interval)

            except Exception as e:
                self._log(f"[错误] {e}")
                time.sleep(0.5)

        self.state_machine.state = FishState.STOPPED
        self.input.reset()
        if hasattr(self, "_on_user_stopped") and self._on_user_stopped:
            self._on_user_stopped()

    # ---- 场景识别 ----

    def _recognize_scene(self, screenshot: np.ndarray) -> dict:
        """
        识别当前屏幕场景。

        Returns:
            识别结果字典，键名与 state_machine.next_state 期望一致
        """
        result = {
            "can_cast": False,
            "fish_bite": False,
            "is_reeling": False,
            "bait_low": False,
            "in_shop": False,
            "in_sell": False,
            "reel_done": False,
        }

        # 检测可抛竿状态（识别抛竿提示图标/文字）
        result["can_cast"] = self.recognizer.is_present(screenshot, "cast_prompt")

        # 检测鱼上钩（识别上钩特效/提示）
        result["fish_bite"] = self.recognizer.is_present(screenshot, "bite_indicator")

        # 检测遛鱼进度条
        result["is_reeling"] = self.recognizer.is_present(screenshot, "progress_bar_bg")

        # 检测遛鱼完成（识别收杆成功提示）
        result["reel_done"] = self.recognizer.is_present(screenshot, "catch_success")

        # 检测鱼饵不足
        result["bait_low"] = self.recognizer.is_present(screenshot, "bait_low_warning")

        # 检测商店界面
        result["in_shop"] = self.recognizer.is_present(screenshot, "shop_title")

        # 检测出售界面
        result["in_sell"] = self.recognizer.is_present(screenshot, "sell_confirm")

        return result

    # ---- 状态动作 ----

    def _execute_entry_actions(self, state: FishState, screenshot: np.ndarray):
        """执行进入某个状态时的初始化动作"""
        actions = self.state_machine.get_state_actions(state)

        for action in actions:
            if self.state_machine.should_stop():
                return
            self._perform_action(action)

        # 状态特定初始化
        if state == FishState.WAITING_BITE:
            self._bite_start_time = time.time()
            self._log("等待鱼上钩...")
            time.sleep(config.cast_animation_wait)

        elif state == FishState.HOOKING:
            self._log("起勾！")
            time.sleep(config.hook_animation_wait)

        elif state == FishState.REELING:
            self._reel_start_time = time.time()
            self._log("遛鱼中...")

        elif state == FishState.SELLING:
            self._log("进入渔获商店出售...")
            time.sleep(1.0)
            # 确认出售（再按一次 A）
            self.input.press_button(GamepadButton.A)
            time.sleep(0.5)
            # 确认
            self.input.press_button(GamepadButton.A)
            time.sleep(2.0)
            # 按 B 返回
            self.input.press_button(GamepadButton.B)
            time.sleep(1.0)

        elif state == FishState.BUYING_BAIT:
            self._log("进入商店购买鱼饵...")
            time.sleep(1.0)
            # 选择鱼饵（假设默认位置，按 A 确认购买）
            self.input.press_button(GamepadButton.A)
            time.sleep(0.5)
            # 确认购买数量
            self.input.press_button(GamepadButton.A)
            time.sleep(1.5)
            # 按 B 返回
            self.input.press_button(GamepadButton.B)
            time.sleep(0.5)
            self.input.press_button(GamepadButton.B)
            time.sleep(1.0)
            self._log("购买完成，继续钓鱼")

    def _execute_continuous_actions(self, state: FishState, screenshot: np.ndarray):
        """执行状态持续动作（每帧调用）"""
        if state == FishState.REELING:
            self._reeling_control(screenshot)

    def _reeling_control(self, screenshot: np.ndarray):
        """遛鱼控制：检测进度条并调整 LT/RT"""
        bar_info = self.recognizer.detect_progress_bar(
            screenshot,
            bar_template="progress_bar_bg",
            float_template="float_marker",
            green_zone_template="green_zone",
        )

        if bar_info is None:
            return  # 未检测到进度条，可能还在动画中

        action = compute_reel_action(bar_info)
        if action == "LT":
            self.input.tap_reel("LT")
        elif action == "RT":
            self.input.tap_reel("RT")
        # "NONE" 时不操作

    def _check_timeouts(self, state: FishState):
        """检查各状态的超时"""
        if state == FishState.WAITING_BITE:
            if time.time() - self._bite_start_time > config.bite_timeout:
                self._log("等待上钩超时，重新抛竿")
                self.state_machine.state = FishState.CASTING

        elif state == FishState.REELING:
            if time.time() - self._reel_start_time > config.reel_timeout:
                self._log("遛鱼超时，鱼可能跑了，重新抛竿")
                self.state_machine._cycle_count += 1
                self.state_machine.state = FishState.CASTING

    # ---- 动作执行 ----

    def _perform_action(self, action: str):
        """执行单个动作指令"""
        action_upper = action.upper()

        if action_upper == "A":
            self.input.press_button(GamepadButton.A)
            self._log("按下 A")
        elif action_upper == "B":
            self.input.press_button(GamepadButton.B)
            self._log("按下 B")
        elif action_upper == "X":
            self.input.press_button(GamepadButton.X)
            self._log("按下 X")
        elif action_upper == "Y":
            self.input.press_button(GamepadButton.Y)
            self._log("按下 Y")
        elif action_upper == "START":
            self.input.press_button(GamepadButton.START)
            self._log("按下 菜单键")
        elif action_upper == "BACK":
            self.input.press_button(GamepadButton.BACK)
            self._log("按下 视图键")
        elif action_upper == "LT":
            self.input.press_trigger(GamepadButton.LT, value=1.0)
            self._log("按下 LT")
        elif action_upper == "RT":
            self.input.press_trigger(GamepadButton.RT, value=1.0)
            self._log("按下 RT")
        elif action_upper.startswith("WAIT_"):
            try:
                seconds = float(action_upper.replace("WAIT_", "").replace("S", ""))
                time.sleep(seconds)
            except ValueError:
                pass

        time.sleep(config.button_interval)
