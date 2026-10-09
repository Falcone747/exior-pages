"""Build everything: concepts, iterations, renders, final favicon set and
the comparative gallery (index.html, self-contained).

usage: python build.py
"""
import base64
import html
import shutil
from io import BytesIO
from pathlib import Path

from PIL import Image

import gen_concepts
import gen_iterations
from render import SIZES, raster

ROOT = Path(__file__).parent
FINAL_SLUG = "r3d-final-aile-avant"

# Scores /5: lisibilité 16 px, reconnaissance de l'espèce, simplicité, originalité.
SCORES = {
    "01-silhouette": (3, 3, 5, 2, "Lisible sur fond clair, disparaît sur onglet sombre. Générique."),
    "02-tuile-noire": (4, 3, 4, 2, "Fonctionne partout ; corps blanc évoque la harfang, pas la chevêche."),
    "03-tuile-jaune": (5, 3, 5, 3, "Meilleur contraste clair/sombre ; les yeux en négatif sont immédiats."),
    "04-geometrique": (3, 2, 5, 3, "Très net mais lu comme un fantôme ; disparaît sur fond sombre."),
    "05-pixel": (4, 3, 3, 4, "Parfaitement net, mais l'aile en escalier fait du bruit. Esthétique rétro."),
    "06-contour": (2, 2, 3, 2, "Le trait de 1 px devient gris à 16 px. Écarté."),
    "07-aile": (2, 3, 3, 3, "L'aile blanche courbe devient une tache grise à 16 px."),
    "08-sourcils": (4, 5, 4, 4, "Les sourcils blancs donnent le regard sévère propre à la chevêche."),
    "09-perchoir": (4, 3, 4, 3, "Le trait jaune ancre bien l'oiseau mais consomme 2 px de hauteur."),
    "10-pastille": (3, 3, 4, 2, "Le cercle rogne la queue ; l'oiseau devient petit."),
    "11-deux-tons": (3, 4, 3, 5, "Meilleur volume trois-quarts à 128 px ; le plan blanc bave à 16 px."),
    "12-galet": (3, 2, 4, 3, "Le trait de cou coupe l'oiseau en deux ; lecture « robot »."),
}
TOP3 = ["08-sourcils", "03-tuile-jaune", "11-deux-tons"]

ITER_NOTES = {
    "08a-sourcils-plats": "Sourcils plats : nets à 16 px, la signature de l'espèce tient.",
    "08b-sourcils-v": "Le V en escalier devient deux points blancs à 16 px.",
    "08c-regard-severe": "Coin d'œil coupé : invisible à 16 px.",
    "03a-tuile-sourcils": "Fusion 03 + 08 : marche sur clair et sombre, mais l'oiseau touche les bords.",
    "03b-tuile-severe": "Sans blanc, le visage perd sa lecture.",
    "03c-tuile-aile": "L'aile verticale blanche se lit comme une rayure.",
    "11a-plastron": "Le plastron casse la silhouette ; lecture « pingouin ».",
    "11b-plastron-tuile": "Même problème sur tuile.",
    "11c-tuile-noire": "Corps blanc → harfang, pas chevêche.",
    "r2a-silhouette": "Devant continu (plus de « B ») ; reste invisible sur fond sombre.",
    "r2b-silhouette-aile": "L'aile en trait blanc donne enfin un oiseau, pas un bloc.",
    "r2c-tuile": "Version compacte avec 2 px de marge : respire dans la tuile.",
    "r2d-tuile-aile": "Aile en négatif jaune : meilleure lecture d'oiseau entier à 32/128.",
    "r2e-tuile-v": "Sourcils en V : bruit à 16 px.",
    "r3a-final": "Aile calée sur une colonne de pixels : nette, mais le dos devient une lanière.",
    "r3b-final-tete-ronde": "Tête plus bombée : moins « chevêche » (tête aplatie).",
    "r3c-final-sans-aile": "Le plus simple, mais redevient un bloc.",
    "r3d-final-aile-avant": "RETENU — aile avancée sur la colonne 6 : nette à 16 px, oiseau entier lisible.",
}


def b64(im):
    buf = BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def render_dir(src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    out = {}
    for s in sorted(src.glob("*.svg")):
        ims = {n: raster(s, n) for n in SIZES}
        for n, im in ims.items():
            im.save(dst / f"{s.stem}-{n}.png")
        out[s.stem] = (s, ims)
    return out


def card(slug, svg_path, ims, note, score=None, highlight=False):
    t = 0
    rows = ""
    if score:
        names = ("Lisibilité 16 px", "Espèce", "Simplicité", "Originalité")
        t = sum(score[:4])
        rows = "".join(
            f'<tr><th>{n}</th><td><span class="bar" style="--v:{v}"></span>{v}/5</td></tr>'
            for n, v in zip(names, score[:4])
        )
        rows = f'<table class="sc">{rows}<tr class="tot"><th>Total</th><td>{t}/20</td></tr></table>'
    p16, p32, p128 = (b64(ims[n]) for n in SIZES)
    return f"""
<article class="card{' hi' if highlight else ''}">
  <header><h3>{html.escape(slug)}</h3></header>
  <div class="real"><span>taille réelle</span>
    <div class="bg l"><img src="{p16}" width="16" height="16" alt=""></div>
    <div class="bg d"><img src="{p16}" width="16" height="16" alt=""></div>
    <div class="bg l"><img src="{p32}" width="32" height="32" alt=""></div>
    <div class="tab"><img src="{p16}" width="16" height="16" alt=""><b>EXIOR</b></div>
  </div>
  <div class="zoom">
    <figure><img class="px" src="{p16}" width="112" height="112" alt=""><figcaption>16 → ×7</figcaption></figure>
    <figure class="dk"><img class="px" src="{p16}" width="112" height="112" alt=""><figcaption>16 sombre</figcaption></figure>
    <figure><img class="px" src="{p32}" width="112" height="112" alt=""><figcaption>32 → ×3.5</figcaption></figure>
    <figure><img src="{p128}" width="112" height="112" alt=""><figcaption>128</figcaption></figure>
  </div>
  {rows}
  <p>{html.escape(note)}</p>
</article>"""


def ico(frames):
    """ICO container with one PNG-encoded frame per size (each rendered
    natively, never downscaled from a larger one)."""
    import struct
    blobs = []
    for im in frames:
        b = BytesIO()
        im.save(b, "PNG")
        blobs.append(b.getvalue())
    head = struct.pack("<HHH", 0, 1, len(frames))
    off = 6 + 16 * len(frames)
    entries = b""
    for im, blob in zip(frames, blobs):
        w, h = im.size
        entries += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(blob), off)
        off += len(blob)
    return head + entries + b"".join(blobs)


def build_final():
    fin = ROOT / "final"
    fin.mkdir(exist_ok=True)
    src = ROOT / "iterations" / f"{FINAL_SLUG}.svg"
    text = src.read_text().replace(' width="16" height="16"', "", 1).replace("Final D aile avancée", "chevêche")
    (fin / "exior-owl.svg").write_text(text)
    ims = {}
    for n in (16, 32, 48, 128, 180):
        ims[n] = raster(fin / "exior-owl.svg", n)
    ims[16].save(fin / "favicon-16.png")
    ims[32].save(fin / "favicon-32.png")
    ims[128].save(fin / "exior-owl-128.png")
    ims[180].save(fin / "apple-touch-icon.png")
    (fin / "favicon.ico").write_bytes(ico([ims[16], ims[32], ims[48]]))
    return ims


def main():
    gen_concepts.main()
    gen_iterations.main()
    shutil.rmtree(ROOT / "renders", ignore_errors=True)
    concepts = render_dir(ROOT / "concepts", ROOT / "renders" / "concepts")
    iters = render_dir(ROOT / "iterations", ROOT / "renders" / "iterations")
    fin = build_final()

    ranked = sorted(SCORES, key=lambda k: -sum(SCORES[k][:4]))
    c_cards = "".join(
        card(f"{s} — {gen_concepts.C[s][0]}", *concepts[s], gen_concepts.C[s][1] + " " + SCORES[s][4],
             SCORES[s], s in TOP3)
        for s in concepts
    )
    rank_rows = "".join(
        f"<tr{' class=top' if s in TOP3 else ''}><td>{i+1}</td><td>{s}</td>"
        + "".join(f"<td>{v}</td>" for v in SCORES[s][:4])
        + f"<td><b>{sum(SCORES[s][:4])}</b></td></tr>"
        for i, s in enumerate(ranked)
    )
    groups = [
        ("Tour 1 — dérivés des 3 meilleurs", [k for k in iters if k[:2] in ("08", "03", "11")]),
        ("Tour 2 — silhouette continue, version tuile compacte, aile", [k for k in iters if k.startswith("r2")]),
        ("Tour 3 — candidats finaux", [k for k in iters if k.startswith("r3")]),
    ]
    i_html = "".join(
        f"<h3 class='round'>{t}</h3><div class='grid'>"
        + "".join(card(k, *iters[k], ITER_NOTES[k], None, k == FINAL_SLUG) for k in ks)
        + "</div>"
        for t, ks in groups
    )
    f16, f32, f128 = b64(fin[16]), b64(fin[32]), b64(fin[128])
    svg_inline = (ROOT / "final" / "exior-owl.svg").read_text()

    page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EXIOR favicon chevêche</title>
<link rel="icon" href="data:image/svg+xml;base64,{base64.b64encode(svg_inline.encode()).decode()}">
<style>
:root{{--bg:#f4f4f2;--fg:#0b0b0b;--mut:#666;--card:#fff;--line:#e2e2de;--y:#ffc400}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#121212;--fg:#f2f2f2;--mut:#9a9a9a;--card:#1c1c1c;--line:#2c2c2c}}}}
:root[data-theme=dark]{{--bg:#121212;--fg:#f2f2f2;--mut:#9a9a9a;--card:#1c1c1c;--line:#2c2c2c}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1240px;margin:0 auto;padding:32px 16px 80px}}
h1{{font-size:28px;margin:0 0 4px}} h2{{margin:48px 0 12px;font-size:20px}}
.lead{{color:var(--mut);max-width:760px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
.card.hi{{border:2px solid var(--y)}}
.card h3{{margin:0 0 10px;font-size:14px}}
.real{{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}}
.real span{{font-size:11px;color:var(--mut);width:100%}}
.bg{{padding:6px;border-radius:6px;line-height:0}} .bg.l{{background:#fff;border:1px solid #ddd}} .bg.d{{background:#202124}}
.tab{{display:flex;align-items:center;gap:6px;background:#dee1e6;color:#202124;border-radius:8px 8px 0 0;padding:6px 10px;font-size:12px}}
.zoom{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:6px;padding:4px;text-align:center}}
figure.dk{{background:#202124;border-color:#202124}}
figure img{{width:100%;height:auto;display:block}}
img.px{{image-rendering:pixelated;image-rendering:crisp-edges}}
figcaption{{font-size:10px;color:#888}}
.sc{{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:12px}}
.sc th{{text-align:left;font-weight:500;color:var(--mut);width:46%}}
.sc td{{white-space:nowrap}} .sc .tot th,.sc .tot td{{font-weight:700;color:var(--fg)}}
.bar{{display:inline-block;height:6px;width:calc(var(--v)*14px);background:var(--y);border-radius:3px;margin-right:6px;vertical-align:middle}}
.card p{{font-size:12.5px;color:var(--mut);margin:6px 0 0}}
table.rank{{border-collapse:collapse;width:100%;max-width:760px;background:var(--card);border-radius:10px;overflow:hidden}}
.rank th,.rank td{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}}
.rank tr.top td{{background:color-mix(in srgb,var(--y) 22%,transparent)}}
.round{{margin:28px 0 10px;font-size:15px}}
.final{{display:flex;gap:24px;flex-wrap:wrap;align-items:flex-end;background:var(--card);border:2px solid var(--y);border-radius:14px;padding:20px}}
.final .px{{width:192px;height:192px}}
.final .big{{width:192px;height:192px}}
.final ul{{margin:0;padding-left:18px;font-size:13px}}
.wrap{{overflow-x:auto}}
</style></head><body><main>
<h1>EXIOR — favicon chevêche d'Athéna</h1>
<p class="lead">12 concepts dessinés directement sur une grille 16×16 (1 unité = 1 pixel), noir / blanc / jaune uniquement.
Chaque carte montre le rendu 16 px à taille réelle (fond clair, fond sombre, onglet), puis agrandi en nearest-neighbor, le 32 px et le 128 px.
Les 3 meilleurs sont bordés de jaune.</p>

<h2>Résultat retenu</h2>
<div class="final">
  <figure><img class="px" src="{f16}" alt="16 px agrandi"><figcaption>16 px ×12</figcaption></figure>
  <figure><img class="px" src="{f32}" alt="32 px agrandi"><figcaption>32 px ×6</figcaption></figure>
  <figure><img class="big" src="{f128}" alt="128 px"><figcaption>128 px</figcaption></figure>
  <div><div class="real"><span>taille réelle</span><div class="bg l"><img src="{f16}" width="16" height="16" alt=""></div><div class="bg d"><img src="{f16}" width="16" height="16" alt=""></div><div class="bg l"><img src="{f32}" width="32" height="32" alt=""></div><div class="tab"><img src="{f16}" width="16" height="16" alt=""><b>EXIOR</b></div></div>
  <ul><li>Oiseau entier : tête ronde aplatie sans aigrettes, corps trapu, aile repliée, queue courte, pattes.</li>
  <li>Corps de trois quarts tourné vers la droite, yeux décalés vers l'observateur.</li>
  <li>Sourcils blancs = regard sévère propre à l'espèce ; yeux jaunes 2×2 px.</li>
  <li>Tuile jaune : lisible sur onglets clairs et sombres.</li>
  <li>Fichiers : <code>final/exior-owl.svg</code>, <code>favicon-16.png</code>, <code>favicon-32.png</code>, <code>favicon.ico</code> (16/32/48).</li></ul></div>
</div>

<h2>Classement des 12 concepts</h2>
<div class="wrap"><table class="rank"><tr><th>#</th><th>Concept</th><th>Lisib. 16</th><th>Espèce</th><th>Simplicité</th><th>Originalité</th><th>Total /20</th></tr>{rank_rows}</table></div>

<h2>Les 12 concepts</h2>
<div class="grid">{c_cards}</div>

<h2>Itérations sur les 3 meilleurs (08 Sourcils, 03 Tuile jaune, 11 Deux tons)</h2>
{i_html}
</main></body></html>
"""
    (ROOT / "index.html").write_text(page)
    print("gallery written")


if __name__ == "__main__":
    main()
