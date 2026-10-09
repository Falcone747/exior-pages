"""Generate the 12 EXIOR little-owl (Athene noctua) favicon concepts.

Every concept is drawn natively on a 16-unit grid (1 unit = 1 pixel at
16x16): eyes, legs and inner details sit on whole pixels, curves are
reserved for the outline. Palette: black, white, yellow only.
"""
from pathlib import Path

K, W, Y = "#0B0B0B", "#FFFFFF", "#FFC400"
OUT = Path(__file__).parent / "concepts"


def svg(body, title):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
        f'width="16" height="16"><title>{title}</title>{body}</svg>\n'
    )


def rect(x, y, w, h, c, rx=0):
    r = f' rx="{rx}"' if rx else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{r} fill="{c}"/>'


# Base silhouette, body facing right, head turned toward the viewer:
# broad flat head without tufts, squat body, short tail down-left.
OWL = (
    "M9 2C11.8 2 13.6 3.3 13.6 5.4C13.6 6.2 13.4 6.8 13 7.3"
    "C13.7 8.5 13.8 10.1 13.4 11.5C12.9 13.2 11.4 14 9 14H6.6L3.2 15.6L1.8 14.4L4.3 12.2"
    "C3.9 11 4 9.1 4.7 7.8C4.5 7.2 4.4 6.6 4.4 5.9C4.4 3.5 6.3 2 9 2Z"
)
EYES = rect(7, 4, 2, 2, Y, 0.35) + rect(10, 4, 2, 2, Y, 0.35)
LEGS = rect(7, 13, 1, 2, K) + rect(10, 13, 1, 2, K)

# Compact version for tiles and badges (fits a 2 px margin).
OWL_T = (
    "M8.6 3C10.9 3 12.4 4.1 12.4 5.9C12.4 6.5 12.2 7 11.9 7.4"
    "C12.5 8.4 12.6 9.8 12.2 11C11.8 12.3 10.6 12.9 8.6 12.9H6.6L3.6 14.6L2.5 13.6L4.6 11.6"
    "C4.3 10.6 4.4 9 5 7.9C4.8 7.4 4.7 6.8 4.7 6.2C4.7 4.2 6.3 3 8.6 3Z"
)
EYES_T = rect(7, 5, 2, 2, Y, 0.35) + rect(10, 5, 2, 2, Y, 0.35)


def legs_t(c):
    return rect(7, 12, 1, 2, c) + rect(9, 12, 1, 2, c)


C = {}

C["01-silhouette"] = (
    "Silhouette",
    "Silhouette pleine, seuls les yeux sont en couleur. Pattes visibles.",
    f'<path d="{OWL}" fill="{K}"/>' + EYES + LEGS,
)

C["02-tuile-noire"] = (
    "Tuile noire",
    "Tuile noire arrondie, oiseau blanc, yeux jaunes à pupille d'un pixel.",
    rect(0, 0, 16, 16, K, 3.5) + f'<path d="{OWL_T}" fill="{W}"/>' + EYES_T
    + rect(8, 6, 1, 1, K) + rect(11, 6, 1, 1, K) + legs_t(W),
)

C["03-tuile-jaune"] = (
    "Tuile jaune",
    "Tuile jaune, oiseau noir ; les yeux sont le fond jaune en négatif.",
    rect(0, 0, 16, 16, Y, 3.5) + f'<path d="{OWL_T}" fill="{K}"/>' + EYES_T + legs_t(K),
)

C["04-geometrique"] = (
    "Géométrique",
    "Construction pure : disque (tête), quart de disque (corps), triangle (queue).",
    f'<circle cx="9" cy="6" r="4.5" fill="{K}"/>'
    f'<path d="M4.5 6H13.5V7.5A6.5 6.5 0 0 1 7 14H4.5Z" fill="{K}"/>'
    f'<path d="M4.5 11L1 15H7Z" fill="{K}"/>'
    + rect(7, 4, 2, 2, Y) + rect(10, 4, 2, 2, Y) + rect(7, 13, 1, 2, K) + rect(10, 12, 1, 3, K),
)

PIX = [
    "................",
    "................",
    "......KKKKK.....",
    ".....KKKKKKKK...",
    "....KKKKKKKKKK..",
    "....KKYYKYYKKK..",
    "....KKYYKYYKKK..",
    "....KKKKKKKKK...",
    "....KKKKKKKKKK..",
    "....KWKKKKKKKK..",
    "....KWKKKKKKKK..",
    "....KKWKKKKKKK..",
    "...KKKKWKKKKK...",
    "..KKK.KKKKKK....",
    ".KK.....K..K....",
    "................",
]


def pixels(rows):
    col = {"K": K, "Y": Y, "W": W}
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            if ch != ".":
                out.append(rect(x, y, run, 1, col[ch]))
            x += run
    return "".join(out)


C["05-pixel"] = (
    "Pixel natif",
    "Dessiné pixel par pixel sur la grille 16×16, aile en escalier blanc.",
    pixels(PIX),
)

C["06-contour"] = (
    "Contour",
    "Monoline 1 px, ventre blanc, aile tracée d'un trait.",
    f'<path d="{OWL}" fill="{W}" stroke="{K}" stroke-width="1.1" stroke-linejoin="round"/>'
    f'<path d="M6.2 8.2C5.6 10 5.8 11.6 6.6 13.4" fill="none" stroke="{K}" stroke-width="1"/>'
    + EYES + LEGS,
)

C["07-aile"] = (
    "Aile repliée",
    "Silhouette noire, aile repliée découpée en blanc sur le dos.",
    f'<path d="{OWL}" fill="{K}"/>'
    f'<path d="M5 7.8C6.6 8.6 7.2 10.6 6.8 12.4C6.6 13.2 6.2 13.7 5.6 14L4.4 12.6C3.9 11 4 9.2 5 7.8Z" fill="{W}"/>'
    + EYES + LEGS,
)

C["08-sourcils"] = (
    "Sourcils",
    "Le regard sévère de l'espèce : sourcils blancs en V au-dessus des yeux.",
    f'<path d="{OWL}" fill="{K}"/>'
    + rect(6, 3, 3, 1, W) + rect(10, 3, 3, 1, W) + rect(9, 4, 1, 1, W)
    + rect(7, 5, 2, 2, Y, 0.35) + rect(10, 5, 2, 2, Y, 0.35) + LEGS,
)

C["09-perchoir"] = (
    "Perchoir",
    "Oiseau posé sur un trait jaune (branche réduite à une ligne de base).",
    f'<g transform="translate(0 -1)"><path d="{OWL}" fill="{K}"/>' + EYES + "</g>"
    + rect(7, 12, 1, 2, K) + rect(10, 12, 1, 2, K) + rect(5, 14, 11, 1.5, Y),
)

C["10-pastille"] = (
    "Pastille",
    "Pastille ronde noire, oiseau blanc, yeux jaunes.",
    f'<circle cx="8" cy="8" r="8" fill="{K}"/><path d="{OWL_T}" fill="{W}"/>' + EYES_T + legs_t(W),
)

C["11-deux-tons"] = (
    "Deux tons",
    "Deux plans : dos et aile noirs, face et poitrail blancs — volume trois quarts.",
    f'<path d="{OWL}" fill="{K}"/>'
    f'<path d="M7 3.4C9.8 2.8 12.6 3.6 12.6 5.6C12.6 6.4 12.3 6.9 11.9 7.5'
    f'C12.6 8.8 12.6 10.4 12 11.8C11.4 12.8 10.2 13.1 8.6 13C9.2 11 8.8 9 7.4 7.8C6.4 7 6.2 4.2 7 3.4Z" fill="{W}"/>'
    + EYES + LEGS,
)

C["12-galet"] = (
    "Galet",
    "Oiseau ramassé en boule, une seule forme ; un trait blanc sépare tête et corps.",
    f'<path d="M8.6 1.6C11.6 1.6 13.8 3.4 13.8 6C13.8 6.7 13.6 7.3 13.3 7.8'
    f'C13.8 8.6 14 9.6 14 10.6C14 13 12 14.4 9 14.4H6.6L1.8 15.2L3.4 13C3.4 11.6 3.2 10 4 8.2'
    f'C3.6 7.6 3.4 6.8 3.4 6C3.4 3.4 5.6 1.6 8.6 1.6Z" fill="{K}"/>'
    + rect(4, 8, 9.5, 1, W)
    + rect(6.5, 4, 2.5, 2.5, Y, 0.5) + rect(10, 4, 2.5, 2.5, Y, 0.5),
)


def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.svg"):
        f.unlink()
    for slug, (title, _, body) in C.items():
        (OUT / f"{slug}.svg").write_text(svg(body, f"EXIOR — {title}"))
    print(len(C), "concepts")


if __name__ == "__main__":
    main()
