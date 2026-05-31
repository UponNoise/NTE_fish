"""
图像识别模块 - 基于 OpenCV 模板匹配
"""

import os
from typing import Optional, Tuple, List

import cv2
import numpy as np

from config import config


class ImageRecognizer:
    """基于模板匹配的图像识别器"""

    def __init__(self, assets_dir: Optional[str] = None):
        self.assets_dir = assets_dir or config.assets_dir
        self._template_cache: dict[str, np.ndarray] = {}

    def _load_template(self, name: str) -> np.ndarray:
        """加载模板图片（带缓存）"""
        if name in self._template_cache:
            return self._template_cache[name]

        # 支持 .png / .jpg
        for ext in (".png", ".jpg", ".jpeg"):
            path = os.path.join(self.assets_dir, f"{name}{ext}")
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    self._template_cache[name] = img
                    return img

        raise FileNotFoundError(f"模板图片未找到: {name}（已搜索 .png/.jpg）")

    def match_template(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        """
        在截图中查找模板。

        Returns:
            (center_x, center_y, confidence) 或 None
        """
        threshold = threshold or config.match_threshold
        template = self._load_template(template_name)

        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            return None

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return (cx, cy, float(max_val))

        return None

    def match_all(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> List[Tuple[int, int, float]]:
        """查找所有匹配位置（多目标匹配）"""
        threshold = threshold or config.match_threshold
        template = self._load_template(template_name)

        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            return []

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]
        locations = np.where(result >= threshold)

        # 非极大值抑制避免重复
        matches: List[Tuple[int, int, float]] = []
        mask = np.zeros(result.shape, dtype=np.uint8)
        for pt in zip(*locations[::-1]):
            if mask[pt[1], pt[0]]:
                continue
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            confidence = float(result[pt[1], pt[0]])
            matches.append((cx, cy, confidence))
            cv2.rectangle(mask, (pt[0], pt[1]), (pt[0] + w, pt[1] + h), 1, -1)

        return matches

    def is_present(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> bool:
        """检查模板是否存在于截图中"""
        return self.match_template(screenshot, template_name, threshold) is not None

    def detect_progress_bar(
        self,
        screenshot: np.ndarray,
        bar_template: str = "progress_bar_bg",
        float_template: str = "float_marker",
        green_zone_template: str = "green_zone",
    ) -> Optional[dict]:
        """
        检测遛鱼进度条状态。

        Returns:
            {
                "bar_left": int,      # 进度条左边界 x
                "bar_right": int,     # 进度条右边界 x
                "bar_y": int,         # 进度条 y 坐标
                "float_x": int,       # 浮标中心 x
                "green_left": int,    # 绿色区域左边界 x
                "green_right": int,   # 绿色区域右边界 x
            }
            或 None（未检测到进度条）
        """
        # 检测进度条背景
        bar = self.match_template(screenshot, bar_template)
        if bar is None:
            return None

        # 检测绿色区域
        green = self.match_template(screenshot, green_zone_template)
        if green is None:
            return None

        # 检测浮标
        float_marker = self.match_template(screenshot, float_template)
        if float_marker is None:
            return None

        # 加载模板获取宽度
        bar_tpl = self._load_template(bar_template)
        green_tpl = self._load_template(green_zone_template)

        bar_w = bar_tpl.shape[1]
        green_w = green_tpl.shape[1]

        return {
            "bar_left": bar[0] - bar_w // 2,
            "bar_right": bar[0] + bar_w // 2,
            "bar_y": bar[1],
            "float_x": float_marker[0],
            "green_left": green[0] - green_w // 2,
            "green_right": green[0] + green_w // 2,
        }

    def clear_cache(self):
        """清除模板缓存"""
        self._template_cache.clear()


# ---- 遛鱼控制逻辑（不依赖类） ----

def compute_reel_action(
    bar_info: dict,
    dead_zone_ratio: Optional[float] = None,
) -> str:
    """
    根据进度条状态计算遛鱼操作。

    Args:
        bar_info: detect_progress_bar 返回的字典
        dead_zone_ratio: 绿色区域内的死区比例

    Returns:
        "LT"  - 需要向左移动
        "RT"  - 需要向右移动
        "NONE" - 在死区内，无需操作
    """
    dz = dead_zone_ratio if dead_zone_ratio is not None else config.reel_dead_zone_ratio

    green_center = (bar_info["green_left"] + bar_info["green_right"]) / 2
    green_half_width = (bar_info["green_right"] - bar_info["green_left"]) / 2
    dead_zone = green_half_width * dz

    float_x = bar_info["float_x"]
    offset = float_x - green_center

    if abs(offset) <= dead_zone:
        return "NONE"
    elif offset < 0:
        return "RT"  # 浮标偏左，需要向右移动
    else:
        return "LT"  # 浮标偏右，需要向左移动
