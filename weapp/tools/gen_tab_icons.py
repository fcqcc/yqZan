# -*- coding: utf-8 -*-
"""生成微信小程序 tabBar 图标（81x81 PNG，透明底）。"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw

SIZE = 162
OUT = 81
GRAY = (153, 153, 153, 255)
ACTIVE = (157, 45, 90, 255)
W = 10  # 线宽（在 162 画布上）


def downscale(im: Image.Image) -> Image.Image:
    return im.resize((OUT, OUT), Image.Resampling.LANCZOS)


def blank() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def save_pair(base: str, draw_fn) -> None:
    root = os.path.join(os.path.dirname(__file__), "..", "images")
    for color, suffix in ((GRAY, ""), (ACTIVE, "_active")):
        im, d = blank()
        draw_fn(d, color)
        path = os.path.join(root, f"tab_{base}{suffix}.png")
        downscale(im).save(path, "PNG", optimize=True)
        print(path, os.path.getsize(path), "bytes")


def icon_home(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    cx, cy = SIZE // 2, SIZE // 2 + 6
    roof = [(cx, cy - 52), (cx + 58, cy - 8), (cx - 58, cy - 8)]
    d.polygon(roof, outline=c, width=W)
    d.rectangle([cx - 52, cy - 8, cx + 52, cy + 48], outline=c, width=W)
    d.rectangle([cx - 14, cy + 8, cx + 14, cy + 46], fill=c)


def icon_note(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    x0, y0 = 38, 32
    x1, y1 = SIZE - 38, SIZE - 28
    r = 14
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=c, width=W)
    pin_x = (x0 + x1) // 2
    d.ellipse([pin_x - 10, y0 - 18, pin_x + 10, y0 + 2], fill=c)
    for i, yy in enumerate((y0 + 36, y0 + 56, y0 + 76)):
        w = 70 - i * 12
        d.line([(x0 + 22, yy), (x0 + 22 + w, yy)], fill=c, width=6)


def icon_card(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    cx, cy = SIZE // 2, SIZE // 2 + 4
    # 信封
    d.polygon(
        [(cx, cy - 42), (cx + 62, cy - 8), (cx + 62, cy + 44), (cx - 62, cy + 44), (cx - 62, cy - 8)],
        outline=c,
        width=W,
    )
    d.line([(cx - 62, cy - 8), (cx, cy + 22), (cx + 62, cy - 8)], fill=c, width=W)
    d.line([(cx - 62, cy - 8), (cx + 62, cy - 8)], fill=c, width=W)


def icon_me(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    cx, cy = SIZE // 2, SIZE // 2
    d.ellipse([cx - 28, cy - 46, cx + 28, cy - 2], outline=c, width=W)
    d.arc([cx - 52, cy + 2, cx + 52, cy + 92], start=200, end=340, fill=c, width=W)


def main() -> None:
    save_pair("home", icon_home)
    save_pair("note", icon_note)
    save_pair("card", icon_card)
    save_pair("me", icon_me)


if __name__ == "__main__":
    main()
