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
    # 出售相关（英文别名 + 中文原名都生成）
    "sell_all":            (80, 36),
    "quick_submit":        (80, 36),
    "confirm":             (60, 32),
    "close":               (32, 32),
    "fish_warehouse":      (48, 48),
    "fish_warehouse2":     (48, 48),
    "go_fishing":          (80, 36),
}

# 中文原名映射（确保代码别名能解析到文件）
ALIAS_FILES: dict[str, str] = {
    "微信截图_20260531175027": "sell_all",
    "微信截图_20260531174925": "quick_submit",
    "微信截图_20260531175512": "confirm",
    "微信截图_20260531175442": "close",
    "渔获仓库":                "fish_warehouse",
    "渔获仓库2":               "fish_warehouse2",
    "微信截图_20260531175556": "go_fishing",
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

    # 1.png 全屏截屏占位（用于 catch_screen_bottom 裁剪）
    create_png(os.path.join(assets_dir, "1.png"), 1721, 997)

    print("\n完成！请用实际游戏截图替换这些占位文件。")


if __name__ == "__main__":
    main()
