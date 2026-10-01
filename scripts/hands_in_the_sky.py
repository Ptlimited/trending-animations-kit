"""Hands in the sky: 5 hands slide in holding cards that flip through real pages.

python scripts/hands_in_the_sky.py my-video/hands.json [--sheet]

hands.json:
{
  "title": "COFFEE SHOPS",
  "subtitle": "1 casual line, 2 lines max",
  "cards": {
    "top": ["pages/a-0.png", "pages/a-1.png"],
    "right": [...], "left": [...], "bottomleft": [...], "bottomright": [...]
  }
}
Paths are relative to the JSON file. Each hand needs at least 1 page. Output lands in out/ next to the JSON.
"""
import math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

DUR, SWAP = 3.2, 0.4

cfg, base = load_config(sys.argv[1] if len(sys.argv) > 1 else fail("give the path to your JSON file"))
only_keys(cfg, {"title", "subtitle", "cards"}, "the config")
cards = obj(cfg, "cards")
only_keys(cards, HANDS, "cards")
lay = layout()["hands"]
work = work_dir(base)
with browser() as pw:
    notes = render_notes(pw, work, need(cfg, "title"), need(cfg, "subtitle"), top=500)

SK = sky()
K = {n: key_hand(PACK / f"hand-{n}.png") for n in HANDS}
PAGES = {}
for n in HANDS:
    lst = cards.get(n)
    if not isinstance(lst, list) or not lst:
        fail(f'"cards" needs a "{n}" list with at least 1 page, like ["pages/a-0.png"]')
    PAGES[n] = [read_rgba(page_path(base, p)) for p in lst]

cache = {}


def card(n, i):
    if (n, i) not in cache:
        s = lay[n]["s"]
        sp = sprite(*K[n], PAGES[n][i])
        cache[(n, i)] = cv2.resize(sp, (int(sp.shape[1] * s), int(sp.shape[0] * s)), interpolation=cv2.INTER_AREA)
    return cache[(n, i)]


def frame(f):
    t = f / FPS
    fr = SK.copy()
    over(fr, notes, 0, int(round(3 * math.sin(2 * math.pi * t / DUR))))
    for j, n in enumerate(HANDS):
        p = lay[n]
        e = (t - p["t0"]) / 0.42
        if e <= 0:
            continue
        dist = (1 - ease_out_back(e)) * 650
        sp = card(n, int(max(t - p["t0"], 0) / SWAP) % len(PAGES[n]))
        hh, ww = sp.shape[:2]
        piv = (ww / 2 - p["d"][0] * ww / 2, hh / 2 - p["d"][1] * hh / 2)
        ang = 1.6 * math.sin(2 * math.pi * (t / DUR) * 2 + j)
        place(fr, sp, int(p["x"] + p["d"][0] * dist), int(p["y"] + p["d"][1] * dist), ang, piv)
    return grain(fr, f)


run(base, "hands-in-the-sky", int(round(DUR * FPS)), frame, "--sheet" in sys.argv)
