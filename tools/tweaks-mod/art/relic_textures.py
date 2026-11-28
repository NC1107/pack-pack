#!/usr/bin/env python3
"""Draw the relic block textures (16x16) into the mod's assets.

    python3 tools/tweaks-mod/art/relic_textures.py

Dark gunmetal plates with a faint teal seam for the hull, dark teal glass with a thin frame for
the windows: the start sub is darker than anything the player can build early on.
"""
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "src/main/resources/assets/packpack_tweaks/textures/block"


def hull() -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            base = 34 + ((x * 7 + y * 13) % 5)  # faint brushed noise
            r, g, b = base - 4, base, base + 8
            if y in (0, 8) or x in (0, 15):  # plate seams
                r, g, b = 22, 26, 32
            if y in (1, 9) and 0 < x < 15:  # light catching the plate edge
                r, g, b = r + 10, g + 12, b + 14
            img.putpixel((x, y), (r, g, b, 255))
    for x, y in ((2, 3), (13, 3), (2, 12), (13, 12)):  # rivets
        img.putpixel((x, y), (70, 78, 88, 255))
        img.putpixel((x + 1, y + 1), (18, 20, 24, 255))
    for x in range(3, 13):  # the teal seam of the old civilisation
        img.putpixel((x, 8), (40, 110, 120, 255))
    return img


def glass() -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            if x in (0, 15) or y in (0, 15):
                img.putpixel((x, y), (26, 30, 38, 255))  # frame, same metal as the hull
            else:
                img.putpixel((x, y), (30, 90, 100, 110))  # dark teal, see-through
    for i in range(3, 7):  # a soft glint
        img.putpixel((i, i - 1), (150, 210, 220, 140))
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    hull().save(OUT / "relic_hull.png")
    glass().save(OUT / "relic_glass.png")
    print(f"wrote {OUT}")
