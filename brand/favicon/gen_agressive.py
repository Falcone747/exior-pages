"""EXIOR owl, aggressive version (closer to the reference image): angular
head with sharp brow ridges, slanted glowing purple eyes, hooked beak,
blade-like feathers sweeping down. 32-unit grid, bold enough for 16 px."""
from io import BytesIO
from pathlib import Path

OUT = Path(__file__).parent / "agressive"
K, W, V, VL, S1, S2, CREAM = "#09090C", "#FFFFFF", "#7C3AED", "#B794FF", "#D4D4DA", "#6E6E78", "#F6F1E6"

BODY = ("M16 3.4C21.6 3.4 26.6 5.6 29.6 9.6L28 11C28.6 14 28 17 26.4 19.6"
        "C26 24 23 28 18.5 31L15.5 31.5C11 29 7 25 6 20C4.4 17.5 3.6 14 4 11"
        "L2.4 9.6C5.4 5.6 10.4 3.4 16 3.4Z")


def owl(outline=True, moon=False):
    bg = ""
    if moon:
        bg = (f'<rect width="32" height="32" rx="7" fill="{K}"/>'
              f'<circle cx="16" cy="12.4" r="13.6" fill="{CREAM}"/>')
    o = f' stroke="{W}" stroke-width="1.8" stroke-linejoin="round" paint-order="stroke"' if outline else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><title>EXIOR</title>' + bg +
        f'<path d="{BODY}" fill="{K}"{o}/>'
        # blade feathers sweeping down
        f'<path d="M7.6 19.4C8.6 23.6 11.4 27.6 15.6 30.4C13 26.8 11.6 23.2 11.2 19.6Z" fill="{S2}"/>'
        f'<path d="M24.4 19.4C23.8 23.4 21.8 27 18.4 30.2C20.4 26.6 21 23.2 20.8 19.6Z" fill="{S2}"/>'
        f'<path d="M12.6 21L16 24.4L19.4 21L16 27.6Z" fill="{S2}"/>'
        # brow ridges: sharp light blades
        f'<path d="M2.8 9.4L15.6 13.6L14.8 14.8L4.6 11.6Z" fill="{S1}"/>'
        f'<path d="M29.2 9.4L16.4 13.6L17.2 14.8L27.4 11.6Z" fill="{S1}"/>'
        # slanted eyes
        f'<path d="M5.4 12.2L14.4 15C14.4 17.4 12.6 19.2 10.2 19.2C7.6 19.2 5.6 17.2 5.4 14.6Z" fill="{V}"/>'
        f'<path d="M26.6 12.2L17.6 15C17.6 17.4 19.4 19.2 21.8 19.2C24.4 19.2 26.4 17.2 26.6 14.6Z" fill="{V}"/>'
        f'<circle cx="10.6" cy="16.4" r="1.7" fill="{K}"/><circle cx="21.4" cy="16.4" r="1.7" fill="{K}"/>'
        f'<circle cx="11.4" cy="15.7" r=".6" fill="{VL}"/><circle cx="22.2" cy="15.7" r=".6" fill="{VL}"/>'
        # hooked beak
        f'<path d="M14.2 15.4H17.8L16.6 20.6L16 21.6L15.4 20.6Z" fill="{S1}"/>'
        "</svg>\n"
    )


VARIANTS = {"a-contour": owl(), "b-lune": owl(outline=False, moon=True)}

def main(final="b-lune"):
    import cairosvg
    from PIL import Image
    from build import ico

    OUT.mkdir(exist_ok=True)
    for k, v in VARIANTS.items():
        (OUT / f"{k}.svg").write_text(v)
    fin = OUT / "final"
    fin.mkdir(exist_ok=True)
    svg = VARIANTS[final]
    (fin / "exior-chouette.svg").write_text(svg)
    ims = {}
    for n in (16, 32, 48, 180, 512):
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=n, output_height=n)
        ims[n] = Image.open(BytesIO(png)).convert("RGBA")
    ims[16].save(fin / "favicon-16.png")
    ims[32].save(fin / "favicon-32.png")
    ims[48].save(fin / "favicon-48.png")
    ims[180].save(fin / "apple-touch-icon.png")
    ims[512].save(fin / "exior-chouette-512.png")
    (fin / "favicon.ico").write_bytes(ico([ims[16], ims[32], ims[48]]))


if __name__ == "__main__":
    main()
