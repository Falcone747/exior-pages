"""Rasterise SVGs at 16, 32 and 128 px and build a contact sheet.

usage: python render.py <svg_dir> <png_dir> [sheet.png]
"""
import sys
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

SIZES = (16, 32, 128)


def raster(svg_path, size):
    data = cairosvg.svg2png(url=str(svg_path), output_width=size, output_height=size)
    return Image.open(BytesIO(data)).convert("RGBA")


def on(bg, im):
    base = Image.new("RGBA", im.size, bg)
    base.alpha_composite(im)
    return base


def main(src, dst, sheet=None):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    svgs = sorted(src.glob("*.svg"))
    rows = []
    for s in svgs:
        ims = {n: raster(s, n) for n in SIZES}
        for n, im in ims.items():
            im.save(dst / f"{s.stem}-{n}.png")
        rows.append((s.stem, ims))
    if not sheet:
        return
    # Each row: 16 px on light/dark (x8 nearest), 32 px x4, 128 px.
    cell = 128
    sw = Image.new("RGB", (cell * 5 + 200, (cell + 16) * len(rows)), "#e8e8e8")
    d = ImageDraw.Draw(sw)
    for i, (name, ims) in enumerate(rows):
        y = i * (cell + 16) + 8
        d.text((6, y + 56), name, fill="black")
        x = 200
        for bg in ("#ffffff", "#202124"):
            sw.paste(on(bg, ims[16]).resize((cell, cell), Image.NEAREST), (x, y)); x += cell
        sw.paste(on("#ffffff", ims[32]).resize((cell, cell), Image.NEAREST), (x, y)); x += cell
        sw.paste(on("#ffffff", ims[128]), (x, y)); x += cell
        sw.paste(on("#ffffff", ims[16]), (x + 56, y + 56))
    sw.save(sheet)


if __name__ == "__main__":
    main(*sys.argv[1:])
