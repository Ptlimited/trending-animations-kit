"""Story grab: a hand holds up a phone playing a 4 slide Instagram story.

python scripts/story_grab.py my-video/story.json [--sheet]

story.json:
{
  "title": "COFFEE SHOPS",
  "subtitle": "1 casual line, 2 lines max",
  "handle": "yourhandle",
  "initials": "YH",
  "slides": [
    {"page": "pages/a-0.png", "colors": ["#E08A6A", "#C4573B"], "crop": "-10%"},
    ... 4 slides ...
  ],
  "stickers": {
    "text": "2 to 4 words",
    "poll": {"question": "A question?", "answers": ["YES", "NOT YET"]},
    "link": "EXAMPLE.COM",
    "question": "Ask me anything about this"
  }
}
"crop" moves the page up inside the story card, in percent of the card width (default "0%").
"""
import math, pathlib, shutil, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

DUR, ST, NSTORY = 5.4, 0.5, 144

cfg, base = load_config(sys.argv[1] if len(sys.argv) > 1 else fail("give the path to your JSON file"))
only_keys(cfg, {"title", "subtitle", "handle", "initials", "slides", "stickers"}, "the config")
slides = need(cfg, "slides")
if not isinstance(slides, list) or len(slides) != 4:
    fail('"slides" needs exactly 4 entries')
st = obj(cfg, "stickers")
only_keys(st, {"text", "poll", "link", "question"}, "stickers")
for k in ("text", "link", "question"):
    need(st, k, "stickers")
poll = obj(st, "poll", "stickers")
only_keys(poll, {"question", "answers"}, "stickers.poll")
need(poll, "question", "stickers.poll")
ans = need(poll, "answers", "stickers.poll")
if not isinstance(ans, list) or len(ans) != 2:
    fail('"stickers.poll.answers" needs exactly 2 answers')
work = work_dir(base)
sdir = work / "story-frames"
shutil.rmtree(sdir, ignore_errors=True)
sdir.mkdir(parents=True)
sheet_only = "--sheet" in sys.argv
NF = int(round(DUR * FPS))
needed = sorted({min(NSTORY - 1, max(0, int((round(i * (NF - 1) / 11) / FPS - ST) * 30))) for i in range(12)}) if sheet_only else range(NSTORY)



def slide(s, i):
    where = f"slides[{i}]"
    if not isinstance(s, dict):
        fail(f"{where} must be an object with page, colors and crop")
    only_keys(s, {"page", "colors", "crop"}, where)
    cols = s.get("colors", ["#444444", "#111111"])
    if not isinstance(cols, list) or len(cols) != 2:
        fail(f'{where}.colors must be 2 hex colors like ["#E08A6A", "#C4573B"]')
    return {"src": page_path(base, need(s, "page", where)).as_uri(), "colors": [color(c, f"{where}.colors") for c in cols],
            "crop": crop(s.get("crop"), f"{where}.crop")}


with browser() as pw:
    notes = render_notes(pw, work, need(cfg, "title"), need(cfg, "subtitle"), top=80)
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 2160})
    pg.goto(template("story.html", work))
    c = {"handle": need(cfg, "handle"), "initials": cfg.get("initials", need(cfg, "handle")[:2].upper()), "stickers": st,
         "slides": [slide(s, i) for i, s in enumerate(slides)]}
    try:
        pg.evaluate("c=>init(c)", c)
    except Exception as e:
        fail(f"a slide page failed to load: {e}")
    for f in needed:
        pg.evaluate(f"render({f / 30})")
        pg.screenshot(path=str(sdir / f"f{f:04d}.png"))
    b.close()

ph = layout()["phone"]
hand, green, box = key_hand(PACK / "hand-phone.png")
S = ph["screen_height_px"] / card_size(box)[1]
hand = cv2.resize(hand, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
green = cv2.resize(green, None, fx=S, fy=S)
box = box * S
X = int(ph["center_x"] - box[:, 0].mean())
Y = int(ph["screen_top_y"] - box[:, 1].min())
SK = sky()


def frame(f):
    t = f / FPS
    fr = SK.copy()
    over(fr, notes, 0, int(round(3 * math.sin(2 * math.pi * t / DUR))))
    sf = min(NSTORY - 1, max(0, int((t - ST) * 30)))
    p = sdir / f"f{sf:04d}.png"
    if not p.exists():
        p = min(sdir.glob("f*.png"), key=lambda q: abs(int(q.stem[1:]) - sf))
    sp = sprite(hand, green, box, cv2.imread(str(p)))
    dy = (1 - ease_out_back((t - ph["t0"]) / 0.45)) * 900
    place(fr, sp, X, int(Y + dy), 1.2 * math.sin(2 * math.pi * t / DUR * 2), (sp.shape[1] / 2, sp.shape[0]))
    return grain(fr, f)


run(base, "story-grab", NF, frame, sheet_only)
shutil.rmtree(sdir, ignore_errors=True)
