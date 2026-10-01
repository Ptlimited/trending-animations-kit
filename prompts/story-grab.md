# Story grab prompt

Paste everything below the line into Claude, Codex or Gemini and add your topic and your Instagram handle.

---

Make me a trending Instagram animation with the free trending animations kit. My topic and Instagram handle are at the end of this prompt. If either is missing, ask me for it. Those are the only questions. Then do the whole thing without stopping for approval.

<what-it-is>
A 5.4 second looping Instagram video: a blue cloud sky, a notes app card with your title, and a real looking hand holding up a phone that plays a 4 slide Instagram story about your topic.
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
You need 4 phone captures, 1 per slide (use --scrolls 0).
It crops the site's menu bar off by itself, prints WARN next to any capture that shows a sign in form, a popup or a bot check, and saves my-video/pages/_overview.png with every capture side by side. Open that 1 image to check them all. Replace any page that has a WARN, an error, a cookie banner or looks empty, using another URL. If capture.py prints ERROR, fix what it names.
Use only words that appear on the pages.
</pages>

<build>
Write my-video/story.json in exactly this shape (the full example is at the top of scripts/story_grab.py):
{"title": "...", "subtitle": "...", "handle": "...", "initials": "AB",
 "slides": [{"page": "pages/a-0.png", "colors": ["#E08A6A", "#C4573B"], "crop": "0%"}, ... 4 slides],
 "stickers": {"text": "...", "poll": {"question": "...", "answers": ["YES", "NOT YET"]}, "link": "EXAMPLE.COM", "question": "..."}}
- "title": 2 or 3 words in caps that name the topic. "subtitle": 1 casual sentence, 2 lines max.
- "handle": my Instagram handle. "initials": 2 letters for the avatar.
- "colors": 2 hex colors per slide for a bold gradient, dark enough for white text.
- "crop": a percent of the card width that moves the page up, so its headline sits near the top of the card. Start at "0%". If the headline sits low on the sheet, try "-10%", then "-20%". Keep it above "-50%".
- "stickers": "text" is 2 to 4 words that name the topic. "poll" is a question with 2 short answers, no percentages. "link" is the real domain of slide 3's page, in caps. "question" invites replies.
Then run: .venv/bin/python scripts/story_grab.py my-video/story.json --sheet
</build>

<finish>
1. Run the script with --sheet. If it prints ERROR, fix what it names in the JSON and run it again.
2. Open the contact sheet it saves in my-video/out. Check: white story text reads on every color, each slide shows its headline, and the stickers sit inside the phone. Fix the JSON or swap pages, then run --sheet again.
3. When the sheet looks right, run the same command without --sheet. It saves the video in my-video/out as v1, v2, v3 and keeps the earlier ones.
4. Open the video and tell me where it is.
</finish>

My topic:
My Instagram handle:
