"""Screenshot real web pages. Several pages per call, 1 browser.

python scripts/capture.py --out my-video/pages name1=https://example.com name2=https://example.org/menu [--desktop] [--scrolls 0,780]

Phone mode (default): 390 CSS px wide at 2x, for tall cards, stamps and story slides.
--desktop: 1280x960 at 1.5x, for the wide bottomleft card in hands in the sky.
The site's fixed or sticky menu bar is cropped off the top automatically (--skip-top N to set it by hand, in CSS px).
Saves <out>/<name>-0.png, <name>-1.png ... per scroll position, prints a WARN line for pages that show a sign in
form or a popup, and saves <out>/_overview.png with every capture side by side, so you can check them all at once.
"""
import argparse, ipaddress, pathlib, sys, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import browser, fail

DISMISS = ["Reject all", "Reject", "Decline", "Necessary only", "Only necessary", "Deny", "No thanks", "Close", "Accept"]
CHECK = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && r.top < innerHeight; };
  const w = [];
  if ([...document.querySelectorAll('input[type=password]')].some(vis)) w.push('sign in form');
  if ([...document.querySelectorAll('[role=dialog],[aria-modal=true]')].some(vis)) w.push('popup');
  const shown = e => { for (let n = e; n && n !== document.body; n = n.parentElement) { const s = getComputedStyle(n);
    if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) < 0.1) return false; } return true; };
  const big = [...document.querySelectorAll('body *')].some(e => { const s = getComputedStyle(e);
    if (s.position !== 'fixed' || !shown(e)) return false; const r = e.getBoundingClientRect();
    const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0)), h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
    const bg = s.backgroundColor; const solid = bg && !/rgba\([^)]*,\s*0\)|transparent/.test(bg);
    return solid && w * h > innerWidth * innerHeight * 0.3; });
  if (big) w.push('large overlay');
  if (/just a moment|access denied|attention required|captcha/i.test(document.title)) w.push('bot check page');
  return w;
}"""
MENU = """() => { let b = 0; for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e);
  if (s.position !== 'fixed' && s.position !== 'sticky') continue; const r = e.getBoundingClientRect();
  if (r.top <= 1 && r.height > 0 && r.height < 220 && r.width > innerWidth * 0.8) b = Math.max(b, r.bottom); }
  return Math.min(Math.round(b), 200); }"""


def safe_url(u):
    p = urllib.parse.urlparse(u)
    if p.scheme not in ("http", "https") or not p.hostname:
        fail(f"only http and https web pages are allowed: {u}")
    host = p.hostname
    if host == "localhost" or host.endswith(".local"):
        fail(f"local addresses are not allowed: {u}")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            fail(f"private addresses are not allowed: {u}")
    except ValueError:
        pass
    return u


ap = argparse.ArgumentParser()
ap.add_argument("pages", nargs="+", help="name=url pairs")
ap.add_argument("--out", required=True)
ap.add_argument("--desktop", action="store_true")
ap.add_argument("--scrolls", default="0,780")
ap.add_argument("--skip-top", type=int, default=None)
a = ap.parse_args()
try:
    scrolls = [int(v) for v in a.scrolls.split(",")]
except ValueError:
    fail("--scrolls must be numbers like 0,780")
VW, VH, DPR = (1280, 960, 1.5) if a.desktop else (390, 780, 2)
if a.skip_top is not None and not 0 <= a.skip_top < VH // 2:
    fail(f"--skip-top must be between 0 and {VH // 2}")
jobs = []
for item in a.pages:
    name, sep, url = item.partition("=")
    if not sep or not name or not url:
        fail(f"write each page as name=url, got {item!r}")
    jobs.append((name, safe_url(url)))
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)

saved = []
with browser() as pw:
    b = pw.chromium.launch()
    for name, url in jobs:
        pg = b.new_context(viewport={"width": VW, "height": VH}, device_scale_factor=DPR).new_page()
        pg.set_default_timeout(15000)
        try:
            r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"WARN {name}: could not open {url} ({str(e).splitlines()[0]}). Pick another page.")
            pg.context.close()
            continue
        if r is not None and r.status >= 400:
            print(f"WARN {name}: {url} returned {r.status}. Pick another page.")
            pg.context.close()
            continue
        pg.wait_for_timeout(3000)
        for label in DISMISS:
            try:
                el = pg.get_by_role("button", name=label, exact=False).first
                if el.is_visible(timeout=300):
                    el.click()
                    pg.wait_for_timeout(500)
                    break
            except Exception:
                pass
        top = a.skip_top if a.skip_top is not None else pg.evaluate(MENU)
        for i, y in enumerate(scrolls):
            pg.evaluate(f"window.scrollTo(0,{y})")
            pg.wait_for_timeout(800)
            if i and abs(pg.evaluate("window.scrollY") - y) > 50:
                print(f"note {name}: page too short to scroll to {y}, skipped")
                break
            p = out / f"{name}-{i}.png"
            pg.screenshot(path=str(p), clip={"x": 0, "y": top, "width": VW, "height": VH - top})
            warn = pg.evaluate(CHECK)
            print(f"{'WARN ' if warn else ''}{p}{'  shows: ' + ', '.join(warn) if warn else ''}")
            saved.append(p)
        pg.context.close()
    b.close()

if saved:
    import cv2, numpy as np
    th = []
    for p in saved:
        im = cv2.imread(str(p))
        im = cv2.resize(im, (int(im.shape[1] * 360 / im.shape[0]), 360), interpolation=cv2.INTER_AREA)
        cv2.putText(im, p.stem, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        th.append(im)
    rows, row, wsum = [], [], 0
    for t in th:
        if wsum + t.shape[1] > 1800 and row:
            rows.append(row); row, wsum = [], 0
        row.append(t); wsum += t.shape[1]
    rows.append(row)
    width = max(sum(t.shape[1] for t in r) for r in rows)
    sheet = np.vstack([np.hstack(r + [np.full((360, width - sum(t.shape[1] for t in r), 3), 255, np.uint8)]) for r in rows])
    cv2.imwrite(str(out / "_overview.png"), sheet)
    print(f"overview: {out / '_overview.png'}")
