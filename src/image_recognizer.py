"""
图像识别模块 - 基于 OpenCV 模板匹配
支持区域裁剪检测（右下角 UI、上半部遛鱼）
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
            坐标相对于传入 screenshot 的左上角
        """
        threshold = threshold or config.match_threshold
        template = self._load_template(template_name)

        if template.shape[0] > screenshot.shape[0] or template.shape[1] > screenshot.shape[1]:
            return None

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return (cx, cy, float(max_val))
        return None

    def match_in_region(
        self,
        screenshot: np.ndarray,
        template_name: str,
        region: Tuple[int, int, int, int],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        """
        在截图的指定区域内查找模板。

        Args:
            region: (x, y, width, height) — 相对于 screenshot 的裁剪区域

        Returns:
            相对于 screenshot 的 (cx, cy, confidence)，或 None
        """
        x, y, w, h = region
        h_img, w_img = screenshot.shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        if w <= 0 or h <= 0:
            return None

        roi = screenshot[y:y+h, x:x+w]
        result = self.match_template(roi, template_name, threshold)
        if result is None:
            return None
        return (result[0] + x, result[1] + y, result[2])

    def is_present(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> bool:
        return self.match_template(screenshot, template_name, threshold) is not None

    # ── 场景级检测 ──

    def detect_bottom_right_ui(
        self,
        screenshot: np.ndarray,
    ) -> Optional[str]:
        """
        检测右下角区域的按键提示 UI。

        裁剪右下角 1/3 区域，依次匹配 'key_e' 和 'key_f' 模板。

        Returns:
            "E" / "F" / None
        """
        h, w = screenshot.shape[:2]
        region = (w * 2 // 3, h * 2 // 3, w // 3, h // 3)

        for key in ("key_e", "key_f"):
            if self.match_in_region(screenshot, key, region, threshold=0.75) is not None:
                return key[-1].upper()
        return None

    def detect_reeling(
        self,
        screenshot: np.ndarray,
    ) -> Optional[dict]:
        """
        在上半部分画面中检测遛鱼元素。

        仅匹配 green_zone 和 float_marker，比较二者 x 坐标。

        Returns:
            {
                "green_x": int,     # green_zone 中心 x
                "float_x": int,     # float_marker 中心 x
                "action": "A"|"D"|"NONE",
            }
            或 None（未检测到进度条元素）
        """
        h, w = screenshot.shape[:2]
        upper = screenshot[0:h//2, :]

        green = self.match_template(upper, "green_zone")
        marker = self.match_template(upper, "float_marker")

        if green is None or marker is None:
            return None

        result = {
            "green_x": green[0],
            "float_x": marker[0],
        }

        # 判断方向：green_zone 在 float_marker 左边 → A，右边 → D
        offset = result["green_x"] - result["float_x"]
        dead_zone = 5  # 像素级死区
        if abs(offset) <= dead_zone:
            result["action"] = "NONE"
        elif offset < 0:
            result["action"] = "A"
        else:
            result["action"] = "D"

        return result

    def detect_bait_exchange_ui(
        self,
        screenshot: np.ndarray,
    ) -> dict:
        """
        检测换鱼饵界面各元素。

        Returns:
            {"exchange_bait": (cx,cy) or None,
             "bait": (cx,cy) or None,
             "exchange": (cx,cy) or None}
        """
        result = {}
        for name in ("exchange_bait", "bait", "exchange"):
            m = self.match_template(screenshot, name)
            result[name] = (m[0], m[1]) if m else None
        return result

    def detect_catch_result(
        self,
        screenshot: np.ndarray,
    ) -> Optional[Tuple[str, int, int]]:
        """
        检测遛鱼结果。

        Returns:
            ("success", cx, cy) 或 ("fail", cx, cy) 或 None
        """
        for name in ("catch_success", "catch_fail"):
            m = self.match_template(screenshot, name)
            if m is not None:
                return (name, m[0], m[1])
        return None

    def clear_cache(self):
        self._template_cache.clear()

