"""
图像识别模块 - 基于 OpenCV 模板匹配。

识别策略:
1. 只把素材目录中的小图当模板；大截图只作为明确别名时使用。
2. 模板匹配自动尝试多种缩放，适配不同分辨率和 UI 缩放。
3. 高频检测限制在画面区域内，降低误判和性能开销。
"""

import os
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from config import config


DEFAULT_SCALES = (1.0, 0.9, 0.8, 0.67, 0.5)
FAST_SCALES = (1.0, 0.8, 0.67, 0.5)

TEMPLATE_ALIASES: dict[str, tuple[str, ...]] = {
    "bait": ("bait",),
    "bait_low_warning": ("bait_low_warning",),
    "bite_indicator": ("bite_indicator",),
    "catch_fail": ("catch_fail",),
    "catch_success": ("catch_success",),
    "exchange": ("exchange",),
    "exchange_bait": ("exchange_bait",),
    "float_marker": ("float_marker",),
    "green_zone": ("green_zone",),
    "key_e": ("key_e",),
    "key_f": ("key_f",),
    "sell_all": ("微信截图_20260531175027",),
    "quick_submit": ("微信截图_20260531174925",),
    "confirm": ("微信截图_20260531175512",),
    "close": ("微信截图_20260531175442",),
    "fish_warehouse": ("渔获仓库", "渔获仓库2"),
    "go_fishing": ("微信截图_20260531175556",),
}


@dataclass(frozen=True)
class Match:
    name: str
    center: Tuple[int, int]
    confidence: float
    scale: float
    size: Tuple[int, int]

    def as_tuple(self) -> Tuple[int, int, float]:
        return (self.center[0], self.center[1], self.confidence)


class ImageRecognizer:
    """基于模板匹配的图像识别器。"""

    def __init__(self, assets_dir: Optional[str] = None):
        self.assets_dir = assets_dir or config.assets_dir
        self._template_cache: dict[str, np.ndarray] = {}

    # ── 模板加载 ──

    def _template_names(self, name: str) -> tuple[str, ...]:
        return TEMPLATE_ALIASES.get(name, (name,))

    def _load_template(self, name: str) -> Optional[np.ndarray]:
        """加载模板图片（带缓存），不存在时返回 None。"""
        if name in self._template_cache:
            return self._template_cache[name]

        for ext in (".png", ".jpg", ".jpeg"):
            path = os.path.join(self.assets_dir, f"{name}{ext}")
            if os.path.exists(path):
                data = np.fromfile(path, dtype=np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if img is not None:
                    self._template_cache[name] = img
                    return img
        return None

    # ── 通用匹配 ──

    @staticmethod
    def _clip_region(
        screenshot: np.ndarray,
        region: Tuple[int, int, int, int],
    ) -> Optional[Tuple[int, int, np.ndarray]]:
        x, y, w, h = region
        h_img, w_img = screenshot.shape[:2]
        x = max(0, min(int(x), w_img - 1))
        y = max(0, min(int(y), h_img - 1))
        w = min(int(w), w_img - x)
        h = min(int(h), h_img - y)
        if w <= 0 or h <= 0:
            return None
        return x, y, screenshot[y:y + h, x:x + w]

    @staticmethod
    def _relative_region(
        screenshot: np.ndarray,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> Tuple[int, int, int, int]:
        h, w = screenshot.shape[:2]
        return (int(w * left), int(h * top), int(w * width), int(h * height))

    def _match_one(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        template_name: str,
        threshold: float,
        scales: Sequence[float],
    ) -> Optional[Match]:
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        templ_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        best: Optional[Match] = None
        h_img, w_img = gray.shape[:2]

        for scale in scales:
            tw = max(1, int(templ_gray.shape[1] * scale))
            th = max(1, int(templ_gray.shape[0] * scale))
            if tw > w_img or th > h_img:
                continue
            if tw < 8 or th < 8:
                continue

            resized = cv2.resize(templ_gray, (tw, th), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val < threshold:
                continue

            match = Match(
                name=template_name,
                center=(max_loc[0] + tw // 2, max_loc[1] + th // 2),
                confidence=float(max_val),
                scale=float(scale),
                size=(tw, th),
            )
            if best is None or match.confidence > best.confidence:
                best = match

        return best

    def find_best(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        scales: Sequence[float] = DEFAULT_SCALES,
    ) -> Optional[Match]:
        """在截图或指定区域中查找模板别名的最佳匹配。"""
        threshold = config.match_threshold if threshold is None else threshold
        origin_x = origin_y = 0
        roi = screenshot

        if region is not None:
            clipped = self._clip_region(screenshot, region)
            if clipped is None:
                return None
            origin_x, origin_y, roi = clipped

        best: Optional[Match] = None
        for name in self._template_names(template_name):
            template = self._load_template(name)
            if template is None:
                continue

            match = self._match_one(roi, template, name, threshold, scales)
            if match is None:
                continue

            adjusted = Match(
                name=match.name,
                center=(match.center[0] + origin_x, match.center[1] + origin_y),
                confidence=match.confidence,
                scale=match.scale,
                size=match.size,
            )
            if best is None or adjusted.confidence > best.confidence:
                best = adjusted

        return best

    def match_template(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        match = self.find_best(screenshot, template_name, threshold)
        return match.as_tuple() if match else None

    def match_in_region(
        self,
        screenshot: np.ndarray,
        template_name: str,
        region: Tuple[int, int, int, int],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        match = self.find_best(screenshot, template_name, threshold, region=region)
        return match.as_tuple() if match else None

    def is_present(
        self,
        screenshot: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
    ) -> bool:
        return self.find_best(screenshot, template_name, threshold) is not None

    # ── 场景级检测 ──

    def detect_bite(self, screenshot: np.ndarray) -> bool:
        """检测鱼上钩提示。"""
        top_region = self._relative_region(screenshot, 0.0, 0.0, 1.0, 0.22)
        return self.find_best(
            screenshot,
            "bite_indicator",
            threshold=0.68,
            region=top_region,
            scales=FAST_SCALES,
        ) is not None

    def detect_bait_low(self, screenshot: np.ndarray) -> bool:
        """检测鱼饵不足提示。"""
        top_region = self._relative_region(screenshot, 0.0, 0.0, 1.0, 0.25)
        return self.find_best(
            screenshot,
            "bait_low_warning",
            threshold=0.68,
            region=top_region,
            scales=FAST_SCALES,
        ) is not None

    def detect_reeling(self, screenshot: np.ndarray) -> Optional[dict]:
        """检测遛鱼条和浮标，并返回应按 A/D/NONE。"""
        upper = self._relative_region(screenshot, 0.0, 0.0, 1.0, 0.25)
        green = self.find_best(screenshot, "green_zone", threshold=0.62, region=upper, scales=FAST_SCALES)
        marker = self.find_best(screenshot, "float_marker", threshold=0.62, region=upper, scales=FAST_SCALES)

        if green is None or marker is None:
            return None

        green_x = green.center[0]
        marker_x = marker.center[0]
        offset = green_x - marker_x
        dead_zone = max(12, int(green.size[0] * 0.12))

        if abs(offset) <= dead_zone:
            action = "NONE"
        elif offset < 0:
            action = "A"
        else:
            action = "D"

        return {
            "green_x": green_x,
            "float_x": marker_x,
            "action": action,
            "confidence": min(green.confidence, marker.confidence),
        }

    def detect_bait_exchange_ui(self, screenshot: np.ndarray) -> dict:
        """检测换鱼饵界面元素。"""
        return {
            "exchange_bait": None,
            "bait": self._center_or_none(self.find_best(screenshot, "bait", threshold=0.68, scales=FAST_SCALES)),
            "exchange": self._center_or_none(self.find_best(screenshot, "exchange", threshold=0.68, scales=FAST_SCALES)),
        }

    def detect_catch_result(self, screenshot: np.ndarray, threshold: float = 0.58) -> Optional[Tuple[str, int, int]]:
        """检测钓鱼成功或失败结果。

        搜索全屏，使用更低阈值和多尺度以适应不同分辨率和 UI 缩放。
        """
        search = self._relative_region(screenshot, 0.0, 0.0, 1.0, 1.0)
        success = self.find_best(screenshot, "catch_success", threshold=threshold, region=search, scales=DEFAULT_SCALES)
        fail = self.find_best(screenshot, "catch_fail", threshold=threshold, region=search, scales=DEFAULT_SCALES)

        if success is None and fail is None:
            return None
        if fail is None or (success is not None and success.confidence >= fail.confidence):
            return ("catch_success", success.center[0], success.center[1])
        return ("catch_fail", fail.center[0], fail.center[1])

    def detect_sell_buy_ui(self, screenshot: np.ndarray) -> dict:
        """检测出售/商店相关按钮。"""
        return {
            "sell_all": self._center_or_none(self.find_best(screenshot, "sell_all", threshold=0.66, scales=FAST_SCALES)),
            "quick_submit": self._center_or_none(self.find_best(screenshot, "quick_submit", threshold=0.66, scales=FAST_SCALES)),
            "confirm": self._center_or_none(self.find_best(screenshot, "confirm", threshold=0.66, scales=FAST_SCALES)),
            "close": self._center_or_none(self.find_best(screenshot, "close", threshold=0.66, scales=FAST_SCALES)),
            "fish_warehouse": self._center_or_none(self.find_best(screenshot, "fish_warehouse", threshold=0.66, scales=FAST_SCALES)),
            "go_fishing": self._center_or_none(self.find_best(screenshot, "go_fishing", threshold=0.66, scales=FAST_SCALES)),
        }

    @staticmethod
    def _center_or_none(match: Optional[Match]) -> Optional[Tuple[int, int]]:
        return match.center if match else None

    def clear_cache(self):
        self._template_cache.clear()
