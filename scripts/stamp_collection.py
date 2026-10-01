"""Stamp collection: 5 hands hold perforated stamps of real pages, then a postmark slams down.

python scripts/stamp_collection.py my-video/stamps.json [--sheet]

stamps.json:
{
  "title": "COFFEE SHOPS",
  "subtitle": "1 casual line, 2 lines max",
  "postmark": {"ring": "COFFEE SHOPS • 1 PROMPT • ", "line1": "OCT", "line2": "2026"},
  "stamps": {
    "top": {"page": "pages/a-0.png", "color": "#C4573B", "label": "BLUE BOTTLE", "crop": "-20%"},
    "right": {...}, "left": {...}, "bottomleft": {...}, "bottomright": {...}
  }
}
"crop" moves the page up inside the stamp, in percent of the stamp width (default "0%").
"""
import math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

DUR, PMT = 3.4, 2.05

cfg, base = load_config(sys.argv[1] if len(sys.argv) > 1 else fail("give the path to your JSON file"))
only_keys(cfg, {"title", "subtitle", "postmark", "stamps"}, "the config")
stamps = obj(cfg, "stamps")
only_keys(stamps, HANDS, "stamps")
pmc = obj(cfg, "postmark")
only_keys(pmc, {"ring", "line1", "line2"}, "postmark")
lay = layout()["hands"]
work = work_dir(base)
K = {n: key_hand(PACK / f"hand-{n}.png") for n in HANDS}

with browser() as pw:
    notes = render_notes(pw, work, need(cfg, "title"), need(cfg, "subtitle"), top=500)
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 1400})
    pg.goto(template("stamp.html", work))
    STAMP = {}
    for n in HANDS:
        s = stamps.get(n)
        if not isinstance(s, dict):
            fail(f'"stamps" needs a "{n}" object with page, color, label and crop')
        only_keys(s, {"page", "color", "label", "crop"}, f"stamps.{n}")
        src = page_path(base, need(s, "page", f'stamps.{n}')).as_uri()
        w, h = card_size(K[n][2])
        sh = 520 if h >= w else 416
        sw = max(26 * 6, int(round(sh * w / h / 26)) * 26)
        try:
            over_ = pg.evaluate("a=>make(...a)", [sw, sh, color(s.get("color", "#C4573B"), f"stamps.{n}.color"), src,
                                                 crop(s.get("crop"), f"stamps.{n}.crop"), need(s, "label", f"stamps.{n}")])
        except Exception as e:
            fail(f"stamp {n} failed to load its page: {e}")
        if over_:
            fail(f'the label for stamps.{n} is too long for the stamp. Use 1 or 2 short words.')
        p = work / f"stamp-{n}.png"
        pg.locator(".stamp").screenshot(path=str(p), omit_background=True)
        STAMP[n] = read_rgba(p)
    pg.goto(template("postmark.html", work))
    pg.evaluate("a=>setPostmark(...a)", [need(pmc, "ring", "postmark"), pmc.get("line1", ""), pmc.get("line2", "")])
    pg.wait_for_timeout(200)
    pg.locator("#host").screenshot(path=str(work / "postmark.png"), omit_background=True)
    b.close()

PM = read_rgba(work / "postmark.png").astype(np.float32) / 255
SK = sky()
SP = {}
for n in HANDS:
    s = lay[n]["s"]
    sp = sprite(*K[n], STAMP[n])
    SP[n] = cv2.resize(sp, (int(sp.shape[1] * s), int(sp.shape[0] * s)), interpolation=cv2.INTER_AREA)


def frame(f):
    t = f / FPS
    fr = SK.copy()
    sx = sy = 0
    sh = t - PMT - 0.12
    if 0 < sh < 0.2:
        a = 6 * (1 - sh / 0.2)
        sx, sy = int(a * math.sin(sh * 90)), int(a * math.cos(sh * 70))
    over(fr, notes, sx, int(round(3 * math.sin(2 * math.pi * t / DUR))) + sy)
    e = min(max((t - PMT) / 0.12, 0), 1)
    if e > 0:
        sc = (1.7 - 0.7 * e) * 0.62
        pm = cv2.resize(PM, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        R = cv2.getRotationMatrix2D((pm.shape[1] / 2, pm.shape[0] / 2), 12, 1.0)
        pm = cv2.warpAffine(pm, R, (pm.shape[1], pm.shape[0]), borderValue=(0, 0, 0, 0))
        pm[..., 3] *= 0.88 * e
        over(fr, pm, int(805 - pm.shape[1] / 2) + sx, int(880 - pm.shape[0] / 2) + sy)
    for j, n in enumerate(HANDS):
        p = lay[n]
        e = (t - p["t0"]) / 0.42
        if e <= 0:
            continue
        dist = (1 - ease_out_back(e)) * 650
        sp = SP[n]
        hh, ww = sp.shape[:2]
        piv = (ww / 2 - p["d"][0] * ww / 2, hh / 2 - p["d"][1] * hh / 2)
        ang = 1.6 * math.sin(2 * math.pi * (t / DUR) * 2 + j)
        place(fr, sp, int(p["x"] + sx + p["d"][0] * dist), int(p["y"] + sy + p["d"][1] * dist), ang, piv)
    return grain(fr, f)


run(base, "stamp-collection", int(round(DUR * FPS)), frame, "--sheet" in sys.argv)
