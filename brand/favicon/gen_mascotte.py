"""EXIOR owl mascot favicon: bold, round, big stern eyes (OpenClaw-style
legibility). Drawn on a 32-unit grid: every feature is >= 2 units (1 px at 16)."""
from pathlib import Path

OUT = Path(__file__).parent / "mascotte"
K, W, V, VL, G = "#0B0B0F", "#FFFFFF", "#7C3AED", "#A78BFA", "#C9C7D1"

BODY = "M16 3C24.3 3 29 8.6 29 15.6C29 24 23.6 30 16 30C8.4 30 3 24 3 15.6C3 8.6 7.7 3 16 3Z"


def owl(body=K, outline=W, iris=V, tile=None):
    t = f'<rect width="32" height="32" rx="8" fill="{tile}"/>' if tile else ""
    o = f' stroke="{outline}" stroke-width="2.2" paint-order="stroke"' if outline else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><title>EXIOR</title>' + t +
        f'<defs><clipPath id="b"><path d="{BODY}"/></clipPath></defs><path d="{BODY}" fill="{body}"{o}/><g clip-path="url(#b)">'
        # wings: two lighter crescents on the flanks
        f'<path d="M4.6 17C4.4 22 6.6 26.4 10 28.4C8.4 25 8 21 8.6 17.6Z" fill="{iris}" opacity=".55"/>'
        f'<path d="M27.4 17C27.6 22 25.4 26.4 22 28.4C23.6 25 24 21 23.4 17.6Z" fill="{iris}" opacity=".55"/>'
        # eyes
        f'<circle cx="10.6" cy="14" r="5.6" fill="{W}"/><circle cx="21.4" cy="14" r="5.6" fill="{W}"/>'
        f'<circle cx="11.2" cy="14.8" r="3.4" fill="{iris}"/><circle cx="20.8" cy="14.8" r="3.4" fill="{iris}"/>'
        f'<circle cx="11.2" cy="14.8" r="1.7" fill="{K}"/><circle cx="20.8" cy="14.8" r="1.7" fill="{K}"/>'
        f'<circle cx="12.2" cy="13.8" r=".8" fill="{W}"/><circle cx="21.8" cy="13.8" r=".8" fill="{W}"/>'
        # stern V brows cut into the eyes
        f'<path d="M3.5 7.5L16 13.2L28.5 7.5V5H3.5Z" fill="{body}"/>'
        "</g>"
        # beak
        f'<path d="M14.2 18.6H17.8L16 22.4Z" fill="{G}"/>'
        # feet
        f'<rect x="11" y="28.6" width="3" height="2.4" rx="1" fill="{iris}"/><rect x="18" y="28.6" width="3" height="2.4" rx="1" fill="{iris}"/>'
        "</svg>\n"
    )


VARIANTS = {
    "a-noire-contour": owl(),
    "b-violette": owl(body="#4C1D95", iris=VL),
    "c-tuile-violette": owl(outline=None, tile=V, iris=VL),
}

def main():
    """Variants + final set: SVG, 16 px hand-placed pixels, 32/48/180/512 from the vector, ICO."""
    import cairosvg
    from io import BytesIO
    from PIL import Image
    from build import ico
    from pix_mascotte import build as pix16

    OUT.mkdir(exist_ok=True)
    for k, v in VARIANTS.items():
        (OUT / f"{k}.svg").write_text(v)
    fin = OUT / "final"
    fin.mkdir(exist_ok=True)
    (fin / "exior-chouette.svg").write_text(VARIANTS["a-noire-contour"])
    ims = {16: pix16()}
    for n in (32, 48, 180, 512):
        png = cairosvg.svg2png(bytestring=VARIANTS["a-noire-contour"].encode(), output_width=n, output_height=n)
        ims[n] = Image.open(BytesIO(png)).convert("RGBA")
    ims[16].save(fin / "favicon-16.png")
    ims[32].save(fin / "favicon-32.png")
    ims[180].save(fin / "apple-touch-icon.png")
    ims[512].save(fin / "exior-chouette-512.png")
    (fin / "favicon.ico").write_bytes(ico([ims[16], ims[32], ims[48]]))


if __name__ == "__main__":
    main()
