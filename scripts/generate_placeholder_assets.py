"""
素材占位生成脚本 —— 生成最小有效 PNG 使模板加载不报错。

⚠ 这些占位图不会匹配任何游戏画面！
请用实际游戏截图替换 assets/ 下的占位文件。
素材规范见 assets/README.md

用法:
    python scripts/generate_placeholder_assets.py
"""

import os
import sys
import struct
import zlib

def create_png(path: str, width: int = 64, height: int = 32):
    """创建最小有效 PNG（纯色半透明）。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    # IHDR
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8bit RGBA

    # IDAT — 每行 filter=0 + RGBA 像素
    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter none
        for x in range(width):
            raw += b"\xff\x80\x40\xc0"  # orange-ish semi-transparent

    compressed = zlib.compress(raw)
    idat = chunk(b"IDAT", compressed)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + idat + chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(png)
    print(f"  ✓ {path} ({width}×{height})")


TEMPLATES: dict[str, tuple[int, int]] = {
    # 钓鱼流程
    "bite_indicator":      (48, 48),
    "green_zone":          (80, 24),
    "float_marker":        (24, 24),
    "catch_success":       (80, 40),
    "catch_fail":          (80, 40),
    # 换鱼饵界面
    "exchange_bait":       (120, 40),
    "bait":                (40, 40),
    "exchange":            (60, 30),
    # 按键提示
    "key_e":               (32, 32),
    "key_f":               (32, 32),
    # 商店/鱼饵
    "bait_low_warning":    (100, 40),
    # 商店/出售
    "shop_sell_all":        (80, 36),
    "shop_quick_submit":    (80, 36),
    "shop_go_fishing":      (80, 36),
    "shop_fish_warehouse":  (48, 48),
    "shop_fish_warehouse_alt": (48, 48),
    # 弹窗
    "dialog_confirm":       (60, 32),
    "dialog_close":         (32, 32),
    # 场景参考
    "scene_catch_screen_full": (1721, 997),
}

# 中文原名映射（确保代码别名能解析到文件）
ALIAS_FILES: dict[str, str] = {
    # 旧英文名
    "sell_all":              "shop_sell_all",
    "quick_submit":          "shop_quick_submit",
    "confirm":               "dialog_confirm",
    "close":                 "dialog_close",
    "fish_warehouse":        "shop_fish_warehouse",
    "fish_warehouse2":       "shop_fish_warehouse_alt",
    "go_fishing":            "shop_go_fishing",
    # 中文旧名
    "微信截图_20260531175027": "shop_sell_all",
    "微信截图_20260531174925": "shop_quick_submit",
    "微信截图_20260531175512": "dialog_confirm",
    "微信截图_20260531175442": "dialog_close",
    "渔获仓库":                "shop_fish_warehouse",
    "渔获仓库2":               "shop_fish_warehouse_alt",
    "微信截图_20260531175556": "shop_go_fishing",
    # 数字旧名
    "1":                      "scene_catch_screen_full",
}


def main():
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    assets_dir = os.path.abspath(assets_dir)
    print(f"生成占位素材到: {assets_dir}")

    for name, (w, h) in TEMPLATES.items():
        create_png(os.path.join(assets_dir, f"{name}.png"), w, h)

    for alias_name, target_name in ALIAS_FILES.items():
        src = os.path.join(assets_dir, f"{target_name}.png")
        dst = os.path.join(assets_dir, f"{alias_name}.png")
        if os.path.exists(src) and not os.path.exists(dst):
            import shutil
            shutil.copy2(src, dst)
            print(f"  → {alias_name}.png (copy of {target_name}.png)")

    print("\n完成！请用实际游戏截图替换这些占位文件。")


if __name__ == "__main__":
    main()
