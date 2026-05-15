# -*- coding: utf-8 -*-
"""
微信小程序 tabBar 图标：每张 < 40KB（建议 81×81 PNG）。
用法：python tools/compress_tabbar_icons.py
"""
from __future__ import annotations

import os

from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "images")
SIZE = 81
MAX_BYTES = 38 * 1024  # 留出余量，避免边界误差

NAMES = [
    "tab_home",
    "tab_home_active",
    "tab_note",
    "tab_note_active",
    "tab_card",
    "tab_card_active",
    "tab_me",
    "tab_me_active",
]


def save_under_cap(im_rgba: Image.Image, path: str) -> int:
    """RGBA -> 白底 RGB 量化 PNG，压到 MAX_BYTES 以下。"""
    rgb = Image.new("RGB", im_rgba.size, (255, 255, 255))
    rgb.paste(im_rgba, mask=im_rgba.split()[3])
    for colors in (128, 96, 64, 48, 32, 24, 16):
        q = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        buf = os.path.dirname(path) or "."
        tmp = path + ".tmp.png"
        q.save(tmp, "PNG", optimize=True, compress_level=9)
        n = os.path.getsize(tmp)
        if n <= MAX_BYTES:
            os.replace(tmp, path)
            return n
        os.remove(tmp)
    # 最后兜底：灰度
    g = rgb.convert("L")
    g.save(path, "PNG", optimize=True, compress_level=9)
    return os.path.getsize(path)


def main() -> None:
    for base in NAMES:
        path = os.path.join(ROOT, base + ".png")
        if not os.path.isfile(path):
            print("skip (missing):", path)
            continue
        im = Image.open(path).convert("RGBA")
        im = im.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        n = save_under_cap(im, path)
        print(f"{base}.png\t{n}\tbytes\t({n/1024:.1f} KB)")


if __name__ == "__main__":
    main()
