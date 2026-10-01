# Hands in the sky prompt

Paste everything below the line into Claude, Codex or Gemini and add your topic.

---

Make me a trending Instagram animation with the free trending animations kit. My topic is at the end of this prompt. If it is missing, ask me for it. That is the only question. Then do the whole thing without stopping for approval.

<what-it-is>
A 3.2 second looping Instagram video: a blue cloud sky, a notes app card with your title, and 5 real looking hands sliding in holding cards that flip through real pages about your topic.
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
You need 12 to 15 phone captures (2 or 3 per card). For the wide bottomleft card, also capture 2 or 3 pages in desktop mode by adding --desktop (use --scrolls 0 there).
It crops the site's menu bar off by itself, prints WARN next to any capture that shows a sign in form, a popup or a bot check, and saves my-video/pages/_overview.png with every capture side by side. Open that 1 image to check them all. Replace any page that has a WARN, an error, a cookie banner or looks empty, using another URL. If capture.py prints ERROR, fix what it names.
Use only words that appear on the pages.
</pages>

<build>
Write my-video/hands.json in exactly this shape (the full example is at the top of scripts/hands_in_the_sky.py):
{"title": "COFFEE SHOPS", "subtitle": "...", "cards": {"top": ["pages/a-0.png", "pages/b-1.png"], "right": [...], "left": [...], "bottomleft": ["pages/desk-0.png", ...], "bottomright": [...]}}
- "title": 2 or 3 words in caps that name the topic.
- "subtitle": 1 casual sentence that tells the viewer what they get, 2 lines max.
- "cards": all 5 names, each a list of 2 or 3 captures. Paths are relative to the JSON. Use the desktop captures for bottomleft.
Then run: .venv/bin/python scripts/hands_in_the_sky.py my-video/hands.json --sheet
</build>

<finish>
1. Run the script with --sheet. If it prints ERROR, fix what it names in the JSON and run it again.
2. Open the contact sheet it saves in my-video/out. Check: every card shows a readable page, no card is empty or plain text, and no hand covers the title. Fix the JSON or swap pages, then run --sheet again.
3. When the sheet looks right, run the same command without --sheet. It saves the video in my-video/out as v1, v2, v3 and keeps the earlier ones.
4. Open the video and tell me where it is.
</finish>

My topic:
