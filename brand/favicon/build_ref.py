"""Favicon set made from the reference owl itself (ref/chouette-reference.webp).

The favicon is a tight crop on the head (eyes, brows, beak, shoulders):
at 16-48 px the whole tall bird would be too small to read, the face is
what carries the owl. Larger sizes keep the full image.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from build import ico

ROOT = Path(__file__).parent
OUT = ROOT / "final-chouette"
HEAD = (388, 150, 948, 710)  # square crop on the head, measured on the 1254 px source


def rounded(im, r=0.22):
    n = im.size[0]
    m = Image.new("L", (n * 4, n * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, n * 4 - 1, n * 4 - 1), int(n * 4 * r), fill=255)
    out = im.convert("RGBA")
    out.putalpha(m.resize((n, n), Image.LANCZOS))
    return out


def main():
    for f in OUT.glob("*"):
        f.unlink()
    OUT.mkdir(exist_ok=True)
    src = Image.open(ROOT / "ref" / "chouette-reference.webp").convert("RGB")
    head = src.crop(HEAD)
    ims = {}
    for n in (16, 32, 48, 180):
        s = head.resize((n, n), Image.LANCZOS)
        if n <= 32:  # keep edges and the purple eyes crisp at tab size
            s = ImageEnhance.Contrast(s).enhance(1.25).filter(ImageFilter.UnsharpMask(1, 60, 0))
        ims[n] = rounded(s)
    ims[16].save(OUT / "favicon-16.png")
    ims[32].save(OUT / "favicon-32.png")
    ims[48].save(OUT / "favicon-48.png")
    ims[180].save(OUT / "apple-touch-icon.png")
    (OUT / "favicon.ico").write_bytes(ico([ims[16], ims[32], ims[48]]))
    src.resize((512, 512), Image.LANCZOS).save(OUT / "chouette-512.png")


if __name__ == "__main__":
    main()
