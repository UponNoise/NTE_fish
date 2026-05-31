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
    "sell_all": ("shop_sell_all", "sell_all", "微信截图_20260531175027"),
    "quick_submit": ("shop_quick_submit", "quick_submit", "微信截图_20260531174925"),
    "confirm": ("dialog_confirm", "confirm", "微信截图_20260531175512"),
    "close": ("dialog_close", "close", "微信截图_20260531175442"),
    "fish_warehouse": (
        "shop_fish_warehouse",
        "shop_fish_warehouse_alt",
        "fish_warehouse",
        "fish_warehouse2",
        "渔获仓库",
        "渔获仓库2",
    ),
    "go_fishing": ("shop_go_fishing", "go_fishing", "微信截图_20260531175556"),
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
        self._missing_templates: set[str] = set()
        self._init_catch_screen_template()

    def _init_catch_screen_template(self) -> None:
        """从 scene_catch_screen_full.png（完整截屏）裁剪底部 UI 区域作为辅助模板。

        不同鱼获的图标会变，但底部 UI 框架/按钮是不变的，
        用这个裁剪区域做辅助匹配，提高 catch_success 的识别率。
        """
        ref = self._load_template("scene_catch_screen_full")
        if ref is None:
            ref = self._load_template("1")
        if ref is None:
            return
        h, w = ref.shape[:2]
        # 裁剪底部 35% 区域（UI 按钮/框架，排除变化的鱼图标）
        crop_top = int(h * 0.65)
        cropped = ref[crop_top:h, 0:w]
        if cropped.size > 0:
            self._template_cache["catch_screen_bottom"] = cropped

    # ── 模板加载 ──

    def _template_names(self, name: str) -> tuple[str, ...]:
        return TEMPLATE_ALIASES.get(name, (name,))

    def _load_template(self, name: str) -> Optional[np.ndarray]:
        """加载模板图片（带缓存），不存在时返回 None 并记录缺失。"""
        if name in self._template_cache:
            return self._template_cache[name]

        for ext in (".png", ".jpg", ".jpeg"):
            path = os.path.join(self.assets_dir, f"{name}{ext}")
            if os.path.exists(path):
                data = np.fromfile(path, dtype=np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if img is not None:
                    self._template_cache[name] = img
                    # 曾经缺失过的话，现在找到就不报警了
                    self._missing_templates.discard(name)
                    return img
        # 仅警告一次
        if name not in self._missing_templates:
            self._missing_templates.add(name)
            import logging
            logging.getLogger("NTE_fish").warning(
                f"[ImageRecognizer] 模板缺失: {name}.png/.jpg 未在 assets/ 中找到"
            )
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

        策略：
        1. 先用 catch_success / catch_fail 小模板精确匹配（全屏、多尺度、低阈值）
        2. 若小模板未命中，用 scene_catch_screen_full.png 底部 UI 裁剪区做场景级匹配
        3. 场景匹配命中后，估算点击位置（底部中央）
        """
        search_full = self._relative_region(screenshot, 0.0, 0.0, 1.0, 1.0)
        success = self.find_best(screenshot, "catch_success", threshold=threshold, region=search_full, scales=DEFAULT_SCALES)
        fail = self.find_best(screenshot, "catch_fail", threshold=threshold, region=search_full, scales=DEFAULT_SCALES)

        if success is not None or fail is not None:
            if fail is None or (success is not None and success.confidence >= fail.confidence):
                return ("catch_success", success.center[0], success.center[1])
            return ("catch_fail", fail.center[0], fail.center[1])

        # 小模板未命中 → 尝试场景级匹配（scene_catch_screen_full.png 底部 UI 裁剪区）
        scene_templ = self._template_cache.get("catch_screen_bottom")
        if scene_templ is not None:
            # 只在截图底部 40% 搜索，与裁剪区域对应
            bottom_region = self._relative_region(screenshot, 0.0, 0.60, 1.0, 0.40)
            scene_match = self.find_best(
                screenshot,
                "catch_screen_bottom",
                threshold=0.50,
                region=bottom_region,
                scales=(1.0, 0.9, 0.8),
            )
            if scene_match is not None:
                # 场景匹配命中 → 点击底部中央
                h, w = screenshot.shape[:2]
                click_x = w // 2
                click_y = int(h * 0.82)
                return ("catch_success", click_x, click_y)

        return None

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

    def list_missing_templates(self) -> list[str]:
        """返回当前缺失的模板名称列表。"""
        return sorted(self._missing_templates)

    def clear_cache(self):
        self._template_cache.clear()
        self._missing_templates.clear()
