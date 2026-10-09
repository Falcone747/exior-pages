"""Iterations on the three best concepts (08 Sourcils, 03 Tuile jaune,
11 Deux tons). Drawn on the 16-unit grid with a new "rounded pixel"
silhouette: straight edges on whole pixels, curves only at corners.
"""
from pathlib import Path

from gen_concepts import K, W, Y, rect, svg

OUT = Path(__file__).parent / "iterations"

# Refined 3/4 silhouette: flat broad head, nape notch on the back,
# chest bulging forward (bird faces right), short blunt tail down-left.
OWL = (
    "M6.5 2H10.5C12.5 2 13.5 3 13.5 5V6.6L13.1 7.4C14 8.2 14.5 9.5 14.5 11"
    "C14.5 13 13 14 11 14H6.4L3 15.4L1.8 14.4L4 12V8.4C4 7.9 4.2 7.4 4.5 7"
    "C4.2 6.6 4 6 4 5.2C4 3.2 5 2 6.5 2Z"
)
LEGS = rect(7, 13, 1, 2, K) + rect(10, 13, 1, 2, K)
EYES = rect(7, 5, 2, 2, Y, 0.3) + rect(10, 5, 2, 2, Y, 0.3)
# Stern eyes: the inner top corner is cut, giving the frowning look.
STERN = (
    f'<path d="M7 5H8.2L9 5.8V7H7Z" fill="{Y}"/>'
    f'<path d="M10.8 5H12V7H10V5.8Z" fill="{Y}"/>'
)
BROWS_FLAT = rect(6, 4, 3, 1, W) + rect(10, 4, 3, 1, W)
BROWS_V = (
    f'<path d="M6 3H7V4H9V5H7V4H6Z" fill="{W}"/>'
    f'<path d="M12 3H13V4H12V5H10V4H12Z" fill="{W}"/>'
)
WING = rect(5, 8, 1, 4, W)
# Black owl on a 16 px tile: same silhouette, tile behind.
TILE_Y = rect(0, 0, 16, 16, Y, 3.5)
TILE_K = rect(0, 0, 16, 16, K, 3.5)
BIB = f'<path d="M10 8H13.2C13.8 8.8 14 9.8 14 11C14 12.4 13 13 11.6 13H10C10.7 11.4 10.7 9.6 10 8Z" fill="{W}"/>'

I = {}
I["08a-sourcils-plats"] = ("Sourcils plats", f'<path d="{OWL}" fill="{K}"/>' + BROWS_FLAT + EYES + LEGS)
I["08b-sourcils-v"] = ("Sourcils en V", f'<path d="{OWL}" fill="{K}"/>' + BROWS_V + EYES + LEGS)
I["08c-regard-severe"] = ("Regard sévère", f'<path d="{OWL}" fill="{K}"/>' + STERN + LEGS)
I["03a-tuile-sourcils"] = ("Tuile + sourcils", TILE_Y + f'<path d="{OWL}" fill="{K}"/>' + BROWS_FLAT + EYES + LEGS)
I["03b-tuile-severe"] = ("Tuile + regard sévère", TILE_Y + f'<path d="{OWL}" fill="{K}"/>' + STERN + LEGS)
I["03c-tuile-aile"] = ("Tuile + aile", TILE_Y + f'<path d="{OWL}" fill="{K}"/>' + BROWS_FLAT + EYES + WING + LEGS)
I["11a-plastron"] = ("Plastron blanc", f'<path d="{OWL}" fill="{K}"/>' + BROWS_FLAT + EYES + BIB + LEGS)
I["11b-plastron-tuile"] = ("Plastron sur tuile", TILE_Y + f'<path d="{OWL}" fill="{K}"/>' + STERN + BIB + LEGS)
I["11c-tuile-noire"] = (
    "Inversé tuile noire",
    TILE_K + f'<path d="{OWL}" fill="{W}"/>' + rect(6, 4, 3, 1, K) + rect(10, 4, 3, 1, K)
    + EYES + rect(8, 6, 1, 1, K) + rect(11, 6, 1, 1, K) + rect(7, 13, 1, 2, W) + rect(10, 13, 1, 2, W),
)

# --- Round 2: smoother continuous front, compact tile version, wing ---
OWL2 = (
    "M6.5 2H10.5C12.4 2 13.5 3.1 13.5 5C13.5 6.6 14.5 8.4 14.5 10.6"
    "C14.5 12.8 13 14 10.6 14H6.4L3 15.4L1.8 14.4L4 12V8.2C4 7.6 4.2 7.2 4.5 6.9"
    "C4.2 6.5 4 6 4 5.2C4 3.2 5 2 6.5 2Z"
)
OWL2T = (
    "M7 3H10.5C12.2 3 13 4 13 5.6C13 7 13.6 8.4 13.6 10C13.6 12 12.3 13 10.2 13"
    "H6.4L3.6 14.3L2.6 13.4L4.4 11.4V8.2C4.4 7.7 4.6 7.3 4.8 7"
    "C4.5 6.6 4.4 6.1 4.4 5.4C4.4 3.8 5.4 3 7 3Z"
)
EYES_T = rect(7, 5, 2, 2, Y, 0.3) + rect(10, 5, 2, 2, Y, 0.3)
BROWS_T = rect(6, 4, 3, 1, W, 0.3) + rect(10, 4, 3, 1, W, 0.3)
LEGS_T = rect(7, 12, 1, 2, K) + rect(10, 12, 1, 2, K)


def wing(c, dx=0, dy=0):
    return (f'<path transform="translate({dx} {dy})" d="M5 8C6.4 9.2 6.8 11 6.4 13.2" fill="none" '
            f'stroke="{c}" stroke-width="1" stroke-linecap="round"/>')


I["r2a-silhouette"] = ("Silhouette v2", f'<path d="{OWL2}" fill="{K}"/>' + BROWS_FLAT + EYES + LEGS)
I["r2b-silhouette-aile"] = ("Silhouette v2 + aile", f'<path d="{OWL2}" fill="{K}"/>' + wing(W) + BROWS_FLAT + EYES + LEGS)
I["r2c-tuile"] = ("Tuile v2", TILE_Y + f'<path d="{OWL2T}" fill="{K}"/>' + BROWS_T + EYES_T + LEGS_T)
I["r2d-tuile-aile"] = ("Tuile v2 + aile", TILE_Y + f'<path d="{OWL2T}" fill="{K}"/>' + wing(Y, 0.3, -0.6) + BROWS_T + EYES_T + LEGS_T)
I["r2e-tuile-v"] = ("Tuile v2 + sourcils V", TILE_Y + f'<path d="{OWL2T}" fill="{K}"/>' + BROWS_V + EYES_T + LEGS_T)

# --- Round 3: wing on a pixel column, softer head (final candidates) ---
OWL3T = (
    "M7.4 3H10C12 3 13 4.1 13 5.8C13 7.1 13.6 8.4 13.6 10C13.6 12 12.3 13 10.2 13"
    "H6.4L3.6 14.3L2.6 13.4L4.4 11.4V8.2C4.4 7.7 4.6 7.3 4.8 7"
    "C4.5 6.6 4.4 6.1 4.4 5.6C4.4 3.9 5.6 3 7.4 3Z"
)
WING3 = f'<path d="M5.5 7.8C6 9.2 6.1 10.8 5.9 12.3C5.8 12.8 5.6 13.2 5.3 13.5" fill="none" stroke="{Y}" stroke-width="1" stroke-linecap="round"/>'
I["r3a-final"] = ("Final A", TILE_Y + f'<path d="{OWL3T}" fill="{K}"/>' + WING3 + BROWS_T + EYES_T + LEGS_T)
I["r3b-final-tete-ronde"] = ("Final B tête ronde", TILE_Y + f'<path d="{OWL2T.replace("M7 3H10.5C12.2 3 13 4 13 5.6", "M8.6 2.8C11.4 2.8 13 4 13 5.8")}" fill="{K}"/>' + WING3 + BROWS_T + EYES_T + LEGS_T)
I["r3c-final-sans-aile"] = ("Final C sans aile", TILE_Y + f'<path d="{OWL3T}" fill="{K}"/>' + BROWS_T + EYES_T + LEGS_T)

WING4 = f'<path d="M6.2 7.9C6.7 9.4 6.8 11 6.5 12.3C6.3 13 5.8 13.4 5.2 13.6" fill="none" stroke="{Y}" stroke-width="1" stroke-linecap="round"/>'
I["r3d-final-aile-avant"] = ("Final D aile avancée", TILE_Y + f'<path d="{OWL3T}" fill="{K}"/>' + WING4 + BROWS_T + EYES_T + LEGS_T)


def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.svg"):
        f.unlink()
    for slug, (title, body) in I.items():
        (OUT / f"{slug}.svg").write_text(svg(body, f"EXIOR — {title}"))
    print(len(I), "iterations")


if __name__ == "__main__":
    main()
