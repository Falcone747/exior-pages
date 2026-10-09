"""EXIOR mark: the owl's face IS the X of EXIOR.

Silver brow blades and cheek blades cross at the beak and draw an X; the
two purple eyes sit in its side wedges. Black head on a cream moon, on a
black tile, like the reference image. 64-unit grid.
"""
from pathlib import Path

OUT = Path(__file__).parent
BLACK, SILVER, MOON, VIOLET, PUPIL, GLINT = "#0A0A0D", "#DCDCE2", "#F4EFE3", "#7C3AED", "#050507", "#EDE4FF"

HEAD = "M32 11C43.5 11 51 18.5 51 29C51 41 43 50.5 32 57C21 50.5 13 41 13 29C13 18.5 20.5 11 32 11Z"


def face(mirror=False):
    t = ' transform="matrix(-1 0 0 1 64 0)"' if mirror else ""
    return (
        f"<g{t}>"
        # brow blade: thick at the temple, needle at the beak
        f'<path d="M11.6 16.4L33.4 33.2L31.6 35.4L11 21.6Z" fill="{SILVER}"/>'
        # cheek blade: lower arm of the X
        f'<path d="M30.6 37.6L18.6 51.4L16.2 49.6L29.4 36.4Z" fill="{SILVER}"/>'
        # slanted eye under the brow
        f'<path d="M14.6 23.4L28.6 31.8C27.6 35 25 36.8 21.8 36.8C17.4 36.8 14.6 33 14.6 28.6Z" fill="{VIOLET}"/>'
        f'<circle cx="22.4" cy="31.6" r="2.7" fill="{PUPIL}"/><circle cx="23.6" cy="30.4" r=".95" fill="{GLINT}"/>'
        "</g>"
    )


MARK_BODY = (
    f'<circle cx="32" cy="29" r="25.5" fill="{MOON}"/>'
    f'<clipPath id="h"><path d="{HEAD}"/></clipPath>'
    f'<path d="{HEAD}" fill="{BLACK}"/>'
    + '<g clip-path="url(#h)">' + face() + face(True) + "</g>"
    + f'<path d="M29.4 35.6H34.6L32 43.2Z" fill="{SILVER}"/>'
)


def mark(tile=True):
    bg = f'<rect width="64" height="64" rx="14" fill="{BLACK}"/>' if tile else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>EXIOR</title>'
            + bg + MARK_BODY + "</svg>\n")


# Geometric wordmark drawn as shapes (no font dependency); the X reuses the blades.
def wordmark(color):
    c = color
    E = f'<path d="M0 0H26V7H8V16.5H23V23.5H8V33H26V40H0Z" fill="{c}"/>'
    X = (f'<path d="M0 0H9L20 16L31 0H40L24.5 20L40 40H31L20 24L9 40H0L15.5 20Z" fill="{c}"/>')
    I = f'<rect width="8" height="40" fill="{c}"/>'
    O = (f'<path d="M20 0C32 0 40 8.4 40 20C40 31.6 32 40 20 40C8 40 0 31.6 0 20C0 8.4 8 0 20 0Z'
         f'M20 7C12.6 7 8 12.4 8 20C8 27.6 12.6 33 20 33C27.4 33 32 27.6 32 20C32 12.4 27.4 7 20 7Z" fill="{c}" fill-rule="evenodd"/>')
    R = (f'<path d="M0 0H18C26 0 31 4.8 31 12C31 17.6 27.8 21.6 22.6 23.2L32 40H23L14.6 24.2H8V40H0Z'
         f'M8 7V17.4H17.6C21 17.4 23 15.4 23 12.2C23 9 21 7 17.6 7Z" fill="{c}" fill-rule="evenodd"/>')
    xs, out = 0, ""
    for g, w in ((E, 26), (X.replace(c, VIOLET), 40), (I, 8), (O, 40), (R, 32)):
        out += f'<g transform="translate({xs} 0)">{g}</g>'
        xs += w + 9
    return out, xs - 9


def lockup(text_color, bg=None):
    wm, w = wordmark(text_color)
    total = 64 + 22 + w
    b = f'<rect width="{total + 32}" height="96" rx="18" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total + 32} 96"><title>EXIOR</title>{b}'
            f'<g transform="translate(16 16)"><rect width="64" height="64" rx="14" fill="{BLACK}"/>{MARK_BODY}</g>'
            f'<g transform="translate({16 + 64 + 22} 28)">{wm}</g></svg>\n')


if __name__ == "__main__":
    (OUT / "exior-mark.svg").write_text(mark())
    (OUT / "exior-mark-sans-tuile.svg").write_text(mark(tile=False))
    (OUT / "exior-logo-clair.svg").write_text(lockup(BLACK))
    (OUT / "exior-logo-sombre.svg").write_text(lockup("#F4F2F8"))


def favicons():
    """favicon.svg + PNG 16/32/48/180/512 + favicon.ico from the mark."""
    import struct
    from io import BytesIO

    import cairosvg
    from PIL import Image

    svg = mark()
    (OUT / "favicon.svg").write_text(svg)
    ims = {}
    for n in (16, 32, 48, 180, 512):
        ims[n] = Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=n, output_height=n)))
    for n in (16, 32, 48):
        ims[n].save(OUT / f"favicon-{n}.png")
    ims[180].save(OUT / "apple-touch-icon.png")
    ims[512].save(OUT / "exior-mark-512.png")
    blobs = []
    for n in (16, 32, 48):
        b = BytesIO(); ims[n].save(b, "PNG"); blobs.append(b.getvalue())
    off = 6 + 16 * 3
    data = struct.pack("<HHH", 0, 1, 3)
    for n, blob in zip((16, 32, 48), blobs):
        data += struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(blob), off); off += len(blob)
    (OUT / "favicon.ico").write_bytes(data + b"".join(blobs))


if __name__ == "__main__":
    favicons()
