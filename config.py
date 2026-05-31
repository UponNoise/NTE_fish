"""
NTE 异环钓鱼自动化脚本 - 配置文件
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class BotConfig:
    """钓鱼机器人全局配置"""

    # ---------- 屏幕捕获 ----------
    # 捕获间隔（秒）
    screen_capture_interval: float = 0.1
    # 屏幕区域（None 表示全屏），格式: (left, top, width, height)
    capture_region: Tuple[int, int, int, int] | None = None

    # ---------- 图像识别 ----------
    # 模板匹配阈值 (0.0 ~ 1.0)，越高越严格
    match_threshold: float = 0.8
    # 资源目录路径
    assets_dir: str = "assets"

    # ---------- 手柄模拟 ----------
    # 按键按下持续时间（秒），太短可能不被识别
    button_press_duration: float = 0.15
    # 按键间隔（秒）
    button_interval: float = 0.3

    # ---------- 状态机超时 ----------
    # 等待鱼上钩超时（秒），超时后重新抛竿
    bite_timeout: float = 30.0
    # 遛鱼最大持续时间（秒）
    reel_timeout: float = 60.0
    # 抛竿后等待动画时间（秒）
    cast_animation_wait: float = 2.0
    # 起勾后等待进入遛鱼界面时间（秒）
    hook_animation_wait: float = 1.0

    # ---------- 遛鱼控制 ----------
    # 进度条检测区域比例（屏幕上方区域），相对于捕获区域
    progress_bar_top_ratio: float = 0.0
    progress_bar_bottom_ratio: float = 0.15
    # LT/RT 按键时长范围（秒），用于微调浮标位置
    reel_press_min: float = 0.03
    reel_press_max: float = 0.12
    # 浮标在绿色区域内的死区比例（不操作），减少抖动
    reel_dead_zone_ratio: float = 0.3

    # ---------- 渔获商店 ----------
    # 鱼饵不足阈值（数量）
    bait_low_threshold: int = 1
    # 购买鱼饵数量
    bait_buy_count: int = 99

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
            return cls(**data)
        return cls()


# 全局默认配置实例
config = BotConfig()
