"""Shared pieces for the 3 animation scripts: keying, compositing, sky, grain, note card, encoding."""
import json, math, os, pathlib, re, shutil, subprocess, sys

import cv2
import numpy as np

W, H, FPS = 1080, 1350, 30
ROOT = pathlib.Path(__file__).resolve().parent.parent
PACK = ROOT / "hand-pack"
TEMPLATES = pathlib.Path(__file__).resolve().parent / "templates"
FONT_URI = (PACK / "Archivo.ttf").as_uri()
HANDS = ["top", "right", "bottomleft", "left", "bottomright"]


def fail(msg):
    sys.exit(f"\nERROR: {msg}\n")


def load_config(path):
    path = pathlib.Path(path).resolve()
    if not path.exists():
        fail(f"config not found: {path}")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"config is not valid JSON: {e}")
    return cfg, path.parent


def need(cfg, key, where="config"):
    if key not in cfg or cfg[key] in ("", None, [], {}):
        fail(f'"{key}" is missing in {where}')
    return cfg[key]


def obj(cfg, key, where="config"):
    v = need(cfg, key, where)
    if not isinstance(v, dict):
        fail(f'"{key}" in {where} must be an object like {{"name": value}}, not {type(v).__name__}')
    return v


def only_keys(d, allowed, where):
    extra = set(d) - set(allowed)
    if extra:
        fail(f"unknown key(s) {sorted(extra)} in {where}. Allowed: {sorted(allowed)}")


def color(v, where):
    if not isinstance(v, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
        fail(f'{where} must be a hex color like "#C4573B", got {v!r}')
    return v


def crop(v, where):
    v = "0%" if v is None else v
    if not isinstance(v, str) or not re.fullmatch(r"-?\d+(\.\d+)?%", v):
        fail(f'{where} must be a percent like "-20%", got {v!r}')
    return v


def page_path(base, rel):
    p = (base / rel).resolve()
    if not p.exists():
        fail(f"page image not found: {p}")
    return p


def layout():
    return json.loads((PACK / "layout.json").read_text(encoding="utf-8"))


def read_rgba(path):
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None:
        fail(f"could not read image: {path}")
    if im.dtype != np.uint8:
        im = (im >> 8).astype(np.uint8) if im.dtype == np.uint16 else np.clip(im, 0, 255).astype(np.uint8)
    if min(im.shape[:2]) < 100:
        fail(f"image is too small (under 100px): {path}")
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    return im


def key_hand(path):
    """Blue screen hand with a green card. Returns hand RGBA (float), green mask, card corners tl,tr,br,bl."""
    im = cv2.imread(str(path))
    if im is None:
        fail(f"hand photo missing: {path}")
    im = im.astype(np.float32)
    B, G, R = im[..., 0], im[..., 1], im[..., 2]
    blue = np.clip((B - np.maximum(R, G) - 25) / 60, 0, 1)
    green = np.clip((G - np.maximum(R, B) - 25) / 60, 0, 1)
    hand = np.clip(1 - blue - green, 0, 1)
    rgb = im.copy()
    rgb[..., 0] = np.minimum(B, np.maximum(R, G) * 0.95)
    rgb[..., 1] = np.minimum(G, np.maximum(R, B))
    hm = cv2.morphologyEx((hand * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours((green > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        fail(f"no green card found in {path}")
    (cx, cy), (w, h), a = cv2.minAreaRect(max(cs, key=cv2.contourArea))
    box = cv2.boxPoints(((cx, cy), (w, h), a))
    box = box[np.argsort(np.arctan2(box[:, 1] - cy, box[:, 0] - cx))].astype(np.float32)
    return np.dstack([rgb / 255, hm.astype(np.float32) / 255]), green, box


def card_size(box):
    return float(np.linalg.norm(box[1] - box[0])), float(np.linalg.norm(box[3] - box[0]))


def sprite(hand, green, box, content):
    """Warp content (uint8 BGR or BGRA, alpha kept) into the green card, hand on top."""
    if content.shape[2] == 3:
        content = np.dstack([content, np.full(content.shape[:2], 255, np.uint8)])
    w, h = card_size(box)
    sh, sw = content.shape[:2]
    ar = w / h
    if sw / sh > ar:
        cw = int(sh * ar)
        content = content[:, (sw - cw) // 2:(sw - cw) // 2 + cw]
    elif sw / sh < ar:
        ch = int(sw / ar)
        content = content[(sh - ch) // 2:(sh - ch) // 2 + ch]
    sh, sw = content.shape[:2]
    hh, ww = green.shape
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]]), box)
    wp = cv2.warpPerspective(content, M, (ww, hh), flags=cv2.INTER_AREA,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)).astype(np.float32) / 255
    a_h = hand[..., 3:4]
    a_c = green[..., None] * wp[..., 3:4] * (1 - a_h)
    rgb = hand[..., :3] * a_h + wp[..., :3] * a_c
    a = np.clip(a_h + a_c, 0, 1)
    out = np.zeros((hh, ww, 4), np.float32)
    out[..., :3] = np.where(a > 1e-4, rgb / np.maximum(a, 1e-4), 0)
    out[..., 3:] = a
    return out


def over(dst, src, ox, oy):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(ox, 0), max(oy, 0), min(ox + w, W), min(oy + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    a = s[..., 3:4]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a


def place(fr, s, x, y, ang, piv):
    hh, ww = s.shape[:2]
    R = cv2.getRotationMatrix2D(piv, ang, 1.0)
    s2 = cv2.warpAffine(s, R, (ww, hh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    sh = np.zeros_like(s2)
    sh[..., 3] = cv2.GaussianBlur(s2[..., 3], (0, 0), 14) * 0.32
    over(fr, sh, x + 14, y + 22)
    over(fr, s2, x, y)


def ease_out_back(x, k=1.4):
    x = min(max(x, 0), 1) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def sky():
    s = cv2.imread(str(PACK / "sky.png"))
    sh, sw = s.shape[:2]
    sc = max(W / sw, H / sh)
    s = cv2.resize(s, (math.ceil(sw * sc), math.ceil(sh * sc)), interpolation=cv2.INTER_AREA)
    oy, ox = (s.shape[0] - H) // 2, (s.shape[1] - W) // 2
    s = s[oy:oy + H, ox:ox + W].astype(np.float32) / 255
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return s * (1 - 0.22 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None]


_GRAIN = [np.random.default_rng(7 + i).normal(0, 1, (H // 2, W // 2)).astype(np.float32) for i in range(6)]


def grain(fr, f):
    return np.clip(fr + cv2.resize(_GRAIN[f % 6], (W, H))[..., None] * 0.035, 0, 1)


def template(name, out_dir, **subs):
    """Copy a template into the work folder with the font and any {{KEY}} filled in."""
    text = (TEMPLATES / name).read_text(encoding="utf-8").replace("{{FONT}}", FONT_URI)
    for k, v in subs.items():
        text = text.replace("{{" + k + "}}", v)
    p = pathlib.Path(out_dir) / name
    p.write_text(text, encoding="utf-8")
    return p.as_uri()


def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("playwright is not installed. Run: pip install -r scripts/requirements.txt && python -m playwright install chromium")
    return sync_playwright()


def render_notes(pw, work, title, subtitle, top=500, tilt=4):
    """The note card as a transparent full frame PNG."""
    pg = pw.chromium.launch().new_page(viewport={"width": W, "height": H})
    pg.goto(template("notes.html", work))
    if not pg.evaluate("document.fonts.load('850 63px Archivo').then(f=>f.length)"):
        fail("the Archivo font did not load from hand-pack/Archivo.ttf")
    if pg.evaluate("([t,s,top,tilt])=>setNotes(t,s,top,tilt)", [title, subtitle, top, tilt]):
        fail(f"the title {title!r} is too long for the note card. Use 2 or 3 short words.")
    out = pathlib.Path(work) / "notes.png"
    pg.locator("#notes").screenshot(path=str(out), omit_background=True)
    pg.context.browser.close()
    return read_rgba(out).astype(np.float32) / 255


def work_dir(base):
    d = pathlib.Path(base) / "out" / "_work"
    d.mkdir(parents=True, exist_ok=True)
    return d


def next_video(base, style):
    d = pathlib.Path(base) / "out"
    n = 1
    while (d / f"{style}-v{n}.mp4").exists():
        n += 1
    return d / f"{style}-v{n}.mp4"


def contact_sheet(frames, path):
    th = [cv2.resize(f, (270, 338), interpolation=cv2.INTER_AREA) for f in frames]
    rows = [np.hstack(th[i:i + 6]) for i in range(0, 12, 6)]
    cv2.imwrite(str(path), np.vstack(rows))
    print(f"contact sheet: {path}")


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        fail("ffmpeg is missing. Run: pip install -r scripts/requirements.txt")


def run(base, style, n_frames, frame_fn, sheet_only):
    """Contact sheet always, full render unless sheet_only."""
    idx = [int(round(i * (n_frames - 1) / 11)) for i in range(12)]
    to8 = lambda fr: (fr * 255).astype(np.uint8)
    contact_sheet([to8(frame_fn(i)) for i in idx], pathlib.Path(base) / "out" / f"{style}-contact-sheet.png")
    if sheet_only:
        return
    out = next_video(base, style)
    p = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
                          "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", str(out)],
                         stdin=subprocess.PIPE)
    for f in range(n_frames):
        p.stdin.write(to8(frame_fn(f)).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        fail("ffmpeg failed to encode the video")
    print(f"video: {out}")
