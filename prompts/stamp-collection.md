# Stamp collection prompt

Paste everything below the line into Claude, Codex or Gemini and add your topic.

---

Make me a trending Instagram animation with the free trending animations kit. My topic is at the end of this prompt. If it is missing, ask me for it. That is the only question. Then do the whole thing without stopping for approval.

<what-it-is>
A 3.4 second looping Instagram video: a blue cloud sky, a notes app card with your title, 5 real looking hands holding perforated postage stamps of real pages about your topic, and a postmark that slams down at the end.
</what-it-is>

<setup>
1. Download and unzip the kit, then work inside it:
   curl -L -o kit.zip https://github.com/Ptlimited/trending-animations-kit/archive/refs/heads/main.zip && tar -xf kit.zip && cd trending-animations-kit-main
2. Make a virtual environment: python3 -m venv .venv (on Windows: python -m venv .venv).
3. Run every Python command below with the venv's own Python: .venv/bin/python (on Windows: .venv\Scripts\python.exe). Shell state does not carry between commands, so never rely on activate.
4. Install: .venv/bin/python -m pip install -r scripts/requirements.txt, then .venv/bin/python -m playwright install chromium (on Linux add --with-deps). ffmpeg comes with the requirements.
5. Make a folder called my-video.
</setup>

<pages>
Pick real public pages about my topic that look good small: big headlines, photos, product shots, bold colors. Skip pages that are mostly plain text, like encyclopedia articles.
Capture them all in 1 call, as name=url pairs:
.venv/bin/python scripts/capture.py --out my-video/pages name1=https://... name2=https://...
You need 5 phone captures, 1 per stamp (use --scrolls 0).
It crops the site's menu bar off by itself, prints WARN next to any capture that shows a sign in form, a popup or a bot check, and saves my-video/pages/_overview.png with every capture side by side. Open that 1 image to check them all. Replace any page that has a WARN, an error, a cookie banner or looks empty, using another URL. If capture.py prints ERROR, fix what it names.
Use only words that appear on the pages.
</pages>

<build>
Write my-video/stamps.json in exactly this shape (the full example is at the top of scripts/stamp_collection.py):
{"title": "...", "subtitle": "...", "postmark": {"ring": "COFFEE SHOPS • 1 PROMPT • ", "line1": "OCT", "line2": "2026"},
 "stamps": {"top": {"page": "pages/a-0.png", "color": "#C4573B", "label": "BLUE BOTTLE", "crop": "0%"}, "right": {...}, "left": {...}, "bottomleft": {...}, "bottomright": {...}}}
- "title": 2 or 3 words in caps that name the topic. "subtitle": 1 casual sentence, 2 lines max.
- "postmark": "ring" is the topic plus a short phrase, ending in " • ". "line1" is this month in 3 letters and "line2" is the year.
- "stamps": all 5 names. "color" is a bold hex color for the stamp frame. "label" is 1 or 2 words in caps from that page's headline (the top stamp is narrow, so keep its label short). "crop" is a percent of the stamp width that moves the page up so its headline shows: start at "0%", try "-20%" or "-30%" if the headline sits low, keep it above "-60%".
Then run: .venv/bin/python scripts/stamp_collection.py my-video/stamps.json --sheet
</build>

<finish>
1. Run the script with --sheet. If it prints ERROR, fix what it names in the JSON and run it again.
2. Open the contact sheet it saves in my-video/out. Check: every stamp shows its page's headline, every label fits, and the postmark does not cover the title. Fix the JSON or swap pages, then run --sheet again.
3. When the sheet looks right, run the same command without --sheet. It saves the video in my-video/out as v1, v2, v3 and keeps the earlier ones.
4. Open the video and tell me where it is.
</finish>

My topic:
