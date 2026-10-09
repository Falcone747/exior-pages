"""Turn the reference owl into a real logo: flat colours, clean vector.

1. smooth the reference, 2. snap every pixel to a strict logo palette
(black, three greys, moon cream, two purples), 3. vectorise with vtracer.
The result keeps the exact drawing of the reference but as flat SVG shapes.
"""
from pathlib import Path

import numpy as np
import vtracer
from PIL import Image, ImageFilter

ROOT = Path(__file__).parent
OUT = ROOT / "logo"
PALETTE = np.array([
    (8, 8, 10),         # black
    (122, 122, 130),    # feather grey
    (214, 214, 220),    # silver (brows, beak, feather edges)
    (250, 247, 238),    # moon cream
    (118, 52, 235),     # purple iris
], dtype=np.uint8)


def posterize(im):
    """Threshold by luminance into flat logo bands; violet pixels -> purple."""
    a = np.asarray(im.convert("RGB"), dtype=float)
    lum = a @ [0.299, 0.587, 0.114]
    idx = np.zeros(lum.shape, dtype=int)
    idx[lum >= 85] = 1
    head = np.zeros(lum.shape, bool)
    head[: int(lum.shape[0] * 0.40)] = True  # silver only on the face: brows, beak
    idx[(lum >= 175) & head] = 2
    idx[lum >= 238] = 3
    idx[(a[..., 2] - a[..., 1]) > 35] = 4
    return Image.fromarray(PALETTE[idx])


def main():
    OUT.mkdir(exist_ok=True)
    src = Image.open(ROOT / "ref" / "chouette-reference.webp").convert("RGB")
    src = src.resize((1024, 1024), Image.LANCZOS).filter(ImageFilter.MedianFilter(9))
    flat = posterize(src).filter(ImageFilter.ModeFilter(15))
    flat.save(OUT / "_flat.png")
    vtracer.convert_image_to_svg_py(
        str(OUT / "_flat.png"), str(OUT / "chouette-logo.svg"),
        colormode="color", hierarchical="stacked", mode="spline",
        filter_speckle=24, color_precision=8, layer_difference=8,
        corner_threshold=60, length_threshold=6, splice_threshold=45, path_precision=2,
    )
    (OUT / "_flat.png").unlink()
    finish()


def finish():
    """Clean SVG header, favicon SVG cropped on the head, PNG/ICO set."""
    import re
    from io import BytesIO

    import cairosvg
    from build import ico

    body = (OUT / "chouette-logo.svg").read_text()
    body = body[body.index("<path"):body.rindex("</svg>")]
    body = re.sub(r'\s*transform="translate\(0,0\)"', "", body)
    logo = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
            "<title>EXIOR</title>" + body + "</svg>\n")
    (OUT / "chouette-logo.svg").write_text(logo)
    # favicon: square on the head, rounded corners
    # favicon: round badge framed on the moon, the owl crossing it
    cx, cy, r = 512, 400, 300
    fav = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{cx - r} {cy - r} {2 * r} {2 * r}"><title>EXIOR</title>'
           f'<defs><clipPath id="r"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>'
           f'<g clip-path="url(#r)">{body}</g></svg>\n')
    (OUT / "favicon.svg").write_text(fav)
    ims = {}
    for k in (16, 32, 48, 180):
        ims[k] = Image.open(BytesIO(cairosvg.svg2png(bytestring=fav.encode(), output_width=k, output_height=k))).convert("RGBA")
    for k in (16, 32, 48):
        ims[k].save(OUT / f"favicon-{k}.png")
    ims[180].save(OUT / "apple-touch-icon.png")
    (OUT / "favicon.ico").write_bytes(ico([ims[16], ims[32], ims[48]]))
    Image.open(BytesIO(cairosvg.svg2png(bytestring=logo.encode(), output_width=1024, output_height=1024))).save(OUT / "chouette-logo-1024.png")


if __name__ == "__main__":
    main()
