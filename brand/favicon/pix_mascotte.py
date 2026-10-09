"""Hand-placed 16x16 version of the mascot (the vector blurs at 16 px).
Rows give the left half; the right half is mirrored."""
from pathlib import Path
from PIL import Image

PAL = {".": None, "W": (255, 255, 255), "K": (11, 11, 15), "V": (124, 58, 237),
       "L": (167, 139, 250), "G": (201, 199, 209)}
HALF = [
    "....WWWW",
    "..WWKKKK",
    ".WKKKKKK",
    "WKKKKKKK",
    "WKWWKKKK",
    "WKWWWWKK",
    "WKWVVVWK",
    "WKWVKVWK",
    "WKWVVVWG",
    "WKKWWWKK",
    "WKLKKKKK",
    "WKLLKKKK",
    ".WKLKKKK",
    ".WKKKKKK",
    "..WWKVVK",
    "....WWWW",
]


def build():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, h in enumerate(HALF):
        row = h + h[::-1]
        for x, ch in enumerate(row):
            if PAL[ch]:
                im.putpixel((x, y), PAL[ch] + (255,))
    return im


if __name__ == "__main__":
    build().save(Path(__file__).parent / "mascotte" / "pix16.png")
