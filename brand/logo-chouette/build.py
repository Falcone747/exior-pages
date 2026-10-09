"""Clean vector logo of the reference owl (reference.webp).

Each part of the drawing (owl silhouette, feather tones, silver
highlights, eyes) is isolated as a mask, smoothed so its outline becomes
a clean curve, then vectorised on its own and filled with one flat
colour. The moon is an exact circle. Result: the same owl, as a flat logo.
"""
import re
import tempfile
from pathlib import Path

import numpy as np
import vtracer
from PIL import Image, ImageFilter

ROOT = Path(__file__).parent
N = 1254
MOON = (623, 506, 399)  # measured on the reference: cx, cy, r

INK, GREY1, GREY2, SILVER, CREAM = "#0A0A0C", "#5A5A63", "#8E8E98", "#DCDCE2", "#F5F0E4"
VIOLET, VIOLET_D, GLINT = "#8B45FF", "#4B1FA8", "#F1EAFF"


def smooth(mask, blur, close=0):
    im = Image.fromarray((mask * 255).astype("uint8"))
    if close:
        im = im.filter(ImageFilter.MaxFilter(close)).filter(ImageFilter.MinFilter(close))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im) > 127


def trace(mask, color, speckle=60):
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "m.png", Path(d) / "m.svg"
        Image.fromarray(np.where(mask, 0, 255).astype("uint8")).convert("RGB").save(src)
        vtracer.convert_image_to_svg_py(str(src), str(dst), colormode="binary", mode="spline",
                                        filter_speckle=speckle, corner_threshold=100,
                                        length_threshold=8, splice_threshold=60, path_precision=1)
        svg = dst.read_text()
    paths = re.findall(r"<path[^>]*/>", svg)
    out = []
    for p in paths:
        p = re.sub(r'fill="[^"]*"', f'fill="{color}"', p)
        out.append(p)
    return "".join(out)


def main():
    a = np.asarray(Image.open(ROOT / "reference.webp").convert("RGB")).astype(float)
    lum = a @ [0.299, 0.587, 0.114]
    yy, xx = np.mgrid[:N, :N]
    cx, cy, r = MOON
    in_moon = (xx - cx) ** 2 + (yy - cy) ** 2 < (r + 6) ** 2
    violet = (a[..., 2] - a[..., 1]) > 30

    # owl: inside the moon anything that is not moon; outside, the lit feathers
    owl = (in_moon & (lum < 225)) | (~in_moon & (lum > 22)) | violet
    owl = smooth(owl, 5, close=9)
    grey1 = smooth(owl & (lum > 70), 5)
    grey2 = smooth(owl & (lum > 105), 3.5)
    core = np.asarray(Image.fromarray((owl * 255).astype("uint8")).filter(ImageFilter.MinFilter(11))) > 127
    silver = smooth(core & (lum > 165) & ~violet, 3)

    layers = [
        trace(owl, INK), trace(grey1, GREY1), trace(silver & (yy > 470) & (yy < 640), SILVER, 40),
    ]
    # eyes and beak are drawn exactly (measured on the reference), not traced
    eye = (
        '<clipPath id="el"><path d="M490 346L648 400V520H490Z"/></clipPath>'
        '<clipPath id="er"><path d="M881 346L723 400V520H881Z"/></clipPath>'
    ) + "".join(
        f'<g clip-path="url(#{cid})"><ellipse cx="{x}" cy="{y}" rx="47" ry="41" fill="{VIOLET_D}"/>'
        f'<ellipse cx="{x}" cy="{y}" rx="39" ry="34" fill="{VIOLET}"/>'
        f'<circle cx="{x}" cy="{y + 2}" r="15" fill="#12081F"/>'
        f'<circle cx="{x + 9}" cy="{y - 4}" r="6" fill="{GLINT}"/></g>'
        for x, y, cid in ((576, 388, "el"), (795, 389, "er")))
    brows = trace(silver & (yy < 470), SILVER, 40)
    beak = (f'<path d="M670 398L724 400L716 432L705 486L699 486L684 432Z" fill="{GREY2}"/>'
            f'<path d="M670 398L697 399L702 486L699 486L684 432Z" fill="{SILVER}"/>')
    layers += [eye, brows, beak]
    moon = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{CREAM}"/>'
    body = moon + "".join(layers)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {N} {N}"><title>EXIOR</title>'
           f'<rect width="{N}" height="{N}" fill="{INK}"/>{body}</svg>\n')
    (ROOT / "chouette-logo.svg").write_text(svg)
    (ROOT / "chouette-logo-transparent.svg").write_text(svg.replace(f'<rect width="{N}" height="{N}" fill="{INK}"/>', ""))
    favicons(body)


def favicons(body):
    """Round badge on the moon, framed on the head and shoulders."""
    import struct
    from io import BytesIO

    import cairosvg

    fx, fy, fr = 685, 470, 300
    fav = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fx - fr} {fy - fr} {2 * fr} {2 * fr}"><title>EXIOR</title>'
           f'<defs><clipPath id="badge"><circle cx="{fx}" cy="{fy}" r="{fr}"/></clipPath></defs>'
           f'<g clip-path="url(#badge)"><rect x="{fx - fr}" y="{fy - fr}" width="{2 * fr}" height="{2 * fr}" fill="{INK}"/>{body}</g></svg>\n')
    (ROOT / "favicon.svg").write_text(fav)
    ims = {n: Image.open(BytesIO(cairosvg.svg2png(bytestring=fav.encode(), output_width=n, output_height=n)))
           for n in (16, 32, 48, 180, 512)}
    for n in (16, 32, 48):
        ims[n].save(ROOT / f"favicon-{n}.png")
    ims[180].save(ROOT / "apple-touch-icon.png")
    ims[512].save(ROOT / "favicon-512.png")
    blobs = []
    for n in (16, 32, 48):
        b = BytesIO(); ims[n].save(b, "PNG"); blobs.append(b.getvalue())
    off, data = 6 + 48, struct.pack("<HHH", 0, 1, 3)
    for n, blob in zip((16, 32, 48), blobs):
        data += struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(blob), off); off += len(blob)
    (ROOT / "favicon.ico").write_bytes(data + b"".join(blobs))


if __name__ == "__main__":
    main()
