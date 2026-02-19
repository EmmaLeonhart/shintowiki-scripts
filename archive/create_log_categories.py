#!/usr/bin/env python3
"""
create_log_categories.py
------------------------

For every odd “Category: …” line in *pages.txt*:

• Collect the following `add Category: …` lines            → *text block A*
• Fetch *all* public log events for that category page      → *text block B*

The script writes  A + B  into the category page (creates if missing,
appends if present) and makes sure the page is also in
[[Category:Log added categories]].

Only three things to edit below:  API_URL, USERNAME, PASSWORD.
"""

# ──── LOGIN / WIKI DETAILS ─────────────────────────────────────────
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"        # bot or user account
PASSWORD = "[REDACTED_SECRET_1]"

PAGES_TXT = "pages.txt"        # input file
LOG_CAT   = "Log added categories"

# ──── standard libs ────────────────────────────────────────────────
import os, sys, re, urllib.parse, datetime
import mwclient
from mwclient.errors import APIError

# -------------------------------------------------------------------
def connect() -> mwclient.Site:
    p = urllib.parse.urlparse(API_URL)
    site = mwclient.Site(p.netloc,
                         path=p.path.rsplit("/api.php", 1)[0] + "/")
    site.login(USERNAME, PASSWORD)
    return site

# -------------------------------------------------------------------
def load_lines() -> list[str]:
    if not os.path.exists(PAGES_TXT):
        sys.exit(f"Missing {PAGES_TXT}")
    with open(PAGES_TXT, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f]

# -------------------------------------------------------------------
def ensure_tag(text: str) -> str:
    tag = f"[[Category:{LOG_CAT}]]"
    return text if tag in text else (text.rstrip() + "\n" + tag + "\n")

# ---------------------------------------------------------------------------
# Build human-readable move/delete/undelete log list for a page
# ---------------------------------------------------------------------------
import datetime

# ---------------------------------------------------------------------------
# Build human-readable move / delete / undelete log list for a page
#             – robust to hidden/suppressed fields                       –
# ---------------------------------------------------------------------------
import datetime

def wiki_logs(site: mwclient.Site, title: str) -> str:
    """
    Return a bullet list (newest → oldest) of move / delete / undelete log
    events for *title*.  Works even when some fields are hidden.
    """
    out: list[str] = []

    for ev in site.api(
        action="query",
        list="logevents",
        letitle=title,
        leprop="timestamp|user|comment|type|action|params",
        lelimit="max",
        format="json",
    )["query"]["logevents"]:

        # ---------- timestamp in portable format ---------------------------
        dt = datetime.datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
        ts = f"{dt:%H:%M}, {dt.day} {dt:%B %Y}"

        user    = ev.get("user", "‹hidden›")
        action  = ev.get("action") or ev.get("type", "log")
        comment = ev.get("comment", "")

        # ---------- extra details (move target, undelete #revs) ------------
        extra = ""
        if ev.get("type") == "move":
            tgt = ev.get("params", {}).get("target_title")
            if tgt:
                extra = f" → {tgt}"
        elif ev.get("type") == "undelete":
            revs = ev.get("params", {}).get("revisions")
            extra = f" ({revs} revisions restored)" if revs else ""

        line = f"* {ts} {user} {action}{extra} {comment}".rstrip()
        out.append(line)

    return "\n".join(out)



# -------------------------------------------------------------------
def process(site: mwclient.Site):
    cur_title: str | None = None
    buf: list[str] = []

    def flush():
        nonlocal cur_title, buf
        if not cur_title:
            return
        print(f"◀︎  writing page: Category:{cur_title}")
        full = f"Category:{cur_title}"
        page = site.pages[full]

        block_a = "\n".join(buf).rstrip()
        block_b = wiki_logs(site, full)

        if page.exists:
            new = page.text().rstrip() + "\n\n" + block_a + "\n\n" + block_b
            summary = "Bot: append logs & add-Category lines"
            action  = "updated"
        else:
            new = block_a + "\n\n" + block_b
            summary = "Bot: create page with logs & add-Category lines"
            action  = "created"

        new = ensure_tag(new)
        try:
            page.save(new, summary=summary)
            print(f"    ✓ {action}")
        except APIError as e:
            print("    ✗ save failed", e.code)

        buf.clear()
        cur_title = None

    # iterate ---------------------------------------------------------
    for ln in load_lines():
        print("→", repr(ln))                     # <-- show every raw line
        if ln.startswith("Category:") and not ln.startswith("add Category:"):
            flush()
            cur_title = ln.split(":",1)[1].strip()
            print(f"▶︎  found main line: {cur_title}")
        elif ln.startswith("add Category:") and cur_title:
            buf.append(ln)
            print("   • collected add-line")
    flush()


# -------------------------------------------------------------------
if __name__ == "__main__":
    s = connect()
    process(s)
    print("Done.")
