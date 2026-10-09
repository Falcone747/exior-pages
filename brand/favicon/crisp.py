"""Crisp rasterisation: render the vector large, then give each target
pixel the majority colour of its block, snapped to the exact palette.
No anti-aliasing, no in-between colours: every pixel is a palette colour
or fully transparent."""
from collections import Counter
from io import BytesIO

import cairosvg
from PIL import Image

PALETTE = [(255, 255, 255), (11, 11, 15), (124, 58, 237), (167, 139, 250), (201, 199, 209)]


def snap(c):
    return min(PALETTE, key=lambda p: sum((a - b) ** 2 for a, b in zip(p, c)))


def crisp(svg_text, size, f=8):
    big = Image.open(BytesIO(cairosvg.svg2png(bytestring=svg_text.encode(),
                     output_width=size * f, output_height=size * f))).convert("RGBA")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = big.load()
    for y in range(size):
        for x in range(size):
            votes = Counter()
            for j in range(f):
                for i in range(f):
                    r, g, b, a = px[x * f + i, y * f + j]
                    if a < 128:
                        votes[None] += 1
                    else:
                        # un-premultiplied colour of the opaque-ish sample
                        votes[snap((r, g, b))] += 1
            c = votes.most_common(1)[0][0]
            if c:
                out.putpixel((x, y), c + (255,))
    return out
