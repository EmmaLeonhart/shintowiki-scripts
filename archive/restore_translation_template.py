#!/usr/bin/env python3
"""
restore_translation_template.py
===============================
For each title in **pages.txt** the bot:
1. Scans the page’s revision history **newest → oldest** until it finds a
   revision containing a `{{translated page|…}}` template.
2. If found, appends that exact template wikitext to the current page bottom
   and saves with summary:

   `Bot: restore {{translated page}} from revID <rev_id>`

3. If *none* of the revisions contain the template, appends a comment:

   `<!-- no {{translated page}} template found in history -->`

Hard‑coded API endpoint / credentials – edit at top.
"""
# >>> edit these >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
# <<< edit <<<

import os, sys, time, re, urllib.parse, mwclient
from mwclient.errors import APIError

PAGES_FILE = "pages.txt"; THROTTLE = 0.4
TPL_RX = re.compile(r"\{\{\s*translated page\s*\|[^}]+}}", re.I | re.S)

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php", 1)[0] + "/")
    s.login(USERNAME, PASSWORD)
    return s

# ─── scan history ─────────────────────────────────────────────────

def find_latest_tpl(page: mwclient.page.Page):
    for rev in page.revisions(dir="newer", prop="ids|content", limit="500"):
        text = rev.get('*') if isinstance(rev, dict) else rev["*"]  # mwclient 0.10 vs 0.9
        m = TPL_RX.search(text)
        if m:
            return m.group(0), rev["revid"] if isinstance(rev, dict) else rev["revid"]
    return None, None

# ─── page update helper ───────────────────────────────────────────

def append_and_save(page, block:str, summary:str):
    new = page.text().rstrip() + "\n" + block + "\n"
    if new == page.text():
        print("  = template already present – skip")
        return
    try:
        page.save(new, summary=summary)
        print("  ✓ saved")
    except APIError as e:
        print("  ! save failed", e.code)

# ─── main loop ────────────────────────────────────────────────────

def load_titles():
    if not os.path.exists(PAGES_FILE):
        sys.exit("Missing pages.txt")
    with open(PAGES_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def main():
    s = site(); print("Logged in")
    for title in load_titles():
        print("→", title)
        pg = s.pages[title]
        if not pg.exists:
            print("  ! page missing – skip"); continue
        tpl, rid = find_latest_tpl(pg)
        if tpl:
            append_and_save(pg, tpl, f"Bot: restore {{translated page}} from revID {rid}")
        else:
            append_and_save(pg, "<!-- no {{translated page}} template found in history -->", "Bot: note missing translated page template")
        time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()
