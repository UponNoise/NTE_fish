"""
NTE 异环钓鱼自动化脚本 - 配置文件
"""

import json
import os
from dataclasses import dataclass, fields
from typing import Tuple


# 分辨率约束
RESOLUTION_MIN = (800, 600)       # 最小 800×600
RESOLUTION_MAX = (3840, 2160)     # 最大 3840×2160


@dataclass
class BotConfig:
    """钓鱼机器人全局配置"""

    # ---------- 窗口捕获 ----------
    # 目标进程名
    target_process: str = "HTGame.exe"
    # 是否使用窗口捕获模式（自动定位游戏窗口），False 则使用 capture_region
    use_window_capture: bool = True
    # 窗口查找重试次数（找不到窗口时）
    window_find_retries: int = 3
    # 窗口查找重试间隔（秒）
    window_find_retry_interval: float = 2.0

    # ---------- 屏幕捕获 ----------
    # 捕获间隔（秒）—— 遛鱼时需要高频响应，从 0.1 降至 0.05
    screen_capture_interval: float = 0.05
    # 屏幕区域（仅在 use_window_capture=False 时生效），格式: (left, top, width, height)
    capture_region: Tuple[int, int, int, int] | None = None

    # ---------- 图像识别 ----------
    # 模板匹配阈值 (0.0 ~ 1.0)，越高越严格
    match_threshold: float = 0.72
    # 资源目录路径
    assets_dir: str = "assets"

    # ---------- 键鼠模拟 ----------
    # 按键按下持续时间（秒），太短可能不被识别
    button_press_duration: float = 0.15
    # 按键间隔（秒）
    button_interval: float = 0.3
    # 输入方式：scan_code / vk / keybd_event
    input_backend: str = "scan_code"
    # 每次发键前尝试聚焦游戏窗口
    auto_focus_input: bool = True

    # ---------- 状态机超时 ----------
    # 等待鱼上钩超时（秒），超时后重新抛竿
    bite_timeout: float = 30.0
    # 遛鱼最大持续时间（秒）
    reel_timeout: float = 60.0
    # 抛竿后等待动画时间（秒）
    cast_animation_wait: float = 1.0
    # 起勾后等待进入遛鱼界面时间（秒）
    hook_animation_wait: float = 0.5

    # ---------- 遛鱼控制 ----------
    # A/D 按键时长（秒）—— 从 0.06 增至 0.10，让浮标移动距离更远
    reel_press_duration: float = 0.10
    # 等待上钩时 F 键间隔（秒）—— bite_indicator 闪现太快，改为定时按 F
    bite_f_interval: float = 2.5

    # ---------- 渔获商店 ----------
    # 鱼饵不足阈值（数量）
    bait_low_threshold: int = 1
    # 购买鱼饵数量
    bait_buy_count: int = 99
    # Sell & Buy 环节（暂留空）

    # ---------- 钓鱼循环 ----------
    # 钓鱼循环次数（0 = 无限）
    max_cycles: int = 0
    # 每次循环间额外等待（秒）
    cycle_interval: float = 1.0

    def save(self, path: str = "config.json") -> None:
        """保存配置到 JSON 文件"""
        data = {k: v for k, v in self.__dict__.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def load(cls, path: str = "config.json") -> "BotConfig":
        """从 JSON 文件加载配置"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid_keys = {field.name for field in fields(cls)}
            data = {key: value for key, value in data.items() if key in valid_keys}
            return cls(**data)
        return cls()


# 全局默认配置实例
config = BotConfig()
