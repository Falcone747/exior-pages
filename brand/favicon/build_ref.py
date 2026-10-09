"""Favicon set from the reference owl (ref/chouette-reference.webp).

32 px and up: the exact reference image, cropped to its content.
16 px: hand-placed pixel adaptation of the same owl (a plain downscale
turns into an unreadable blob at that size).
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
OUT = ROOT / "final-chouette"
CROP = (67, 93, 1177, 1203)  # square around moon + owl, measured on 1254 px

PAL = {
    ".": (0, 0, 0), "W": (250, 247, 240), "l": (205, 205, 205),
    "g": (138, 138, 138), "d": (70, 70, 70), "p": (138, 77, 255), "P": (190, 150, 255),
}
PIX16 = [
    "....WWWWWWWW....",
    "..WWWWWWWWWWWW..",
    ".WWW..dddd..WWW.",
    ".WW.l......l.WW.",
    "WWW..ll..ll..WWW",
    "WW...pp..pp...WW",
    "WW...pP.gPp...WW",
    "WW......g.....WW",
    ".W..gl.....lg.W.",
    ".WW.ggl.lg.ggWW.",
    "..Wggl.lgg.ggW..",
    "..lgg.lgg.gg....",
    "..lg.lgg.g......",
    "..lg.lg.g.......",
    "...g.lg.........",
    "....g...........",
]


def pix(rows):
    im = Image.new("RGB", (16, 16))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            im.putpixel((x, y), PAL[ch])
    return im


def ico(frames):
    import struct
    from io import BytesIO
    blobs = []
    for im in frames:
        b = BytesIO(); im.save(b, "PNG"); blobs.append(b.getvalue())
    off = 6 + 16 * len(frames)
    head = struct.pack("<HHH", 0, 1, len(frames)); ent = b""
    for im, blob in zip(frames, blobs):
        ent += struct.pack("<BBBBHHII", im.size[0] % 256, im.size[1] % 256, 0, 0, 1, 32, len(blob), off)
        off += len(blob)
    return head + ent + b"".join(blobs)


def main():
    OUT.mkdir(exist_ok=True)
    src = Image.open(ROOT / "ref" / "chouette-reference.webp").convert("RGB").crop(CROP)
    sizes = {n: src.resize((n, n), Image.LANCZOS) for n in (32, 48, 128, 180, 512)}
    sizes[16] = pix(PIX16)
    sizes[16].save(OUT / "favicon-16.png")
    sizes[32].save(OUT / "favicon-32.png")
    sizes[128].save(OUT / "chouette-128.png")
    sizes[180].save(OUT / "apple-touch-icon.png")
    sizes[512].save(OUT / "chouette-512.png")
    (OUT / "favicon.ico").write_bytes(ico([sizes[16], sizes[32], sizes[48]]))
    return sizes


if __name__ == "__main__":
    main()
