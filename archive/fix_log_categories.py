#!/usr/bin/env python3
"""
fix_log_categories.py  –  v2  (titles & move-targets in the log)
================================================================

Repairs the pages produced by *create_log_categories.py*:

  • turns the leading “add Category: …” into a real category wikilink;
  • prepends a full Special:Log-style block (headed **ACTUAL LOG**);
  • pushes whatever was there before under  == Old Content == ;
  • appends [[Category:Log added categories]].

All titles are taken from pages.txt (one “Category:Foo Bar” per line).
"""

# ─── settings ──────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
PAGES_TXT = "pages.txt"
THROTTLE  = 0.4          # seconds between edits
# ------------------------------------------------------------------

import os, re, time, sys, datetime as dt, urllib.parse
import mwclient
from mwclient.errors import APIError

# fix first line such as:   add Category:7 members)
ADD_RX = re.compile(r"^\s*add\s+Category:(.+\))", re.I)

# ─── portable %-d / %#d helper (Unix vs Windows) ───────────────────
def pretty_date(ts_iso: str) -> str:
    d = dt.datetime.strptime(ts_iso, "%Y-%m-%dT%H:%M:%SZ")
    try:   return d.strftime("%H:%M, %-d %B %Y")   # Unix / Linux
    except ValueError:
           return d.strftime("%H:%M, %#d %B %Y")   # Windows

# ─── convert one logevents JSON entry to a bullet line ─────────────
def log_bullet(e: dict) -> str:
    ts   = pretty_date(e["timestamp"])
    usr  = e.get("user", "")
    act  = e.get("action", "")        # create / move / delete / upload …
    page = e.get("title", "")
    cmt  = e.get("comment", "")
    prm  = e.get("params", {})

    # craft English-like messages for the common actions
    if act == "move":
        tgt = prm.get("target_title", "")
        extra = f"moved page [[{page}]] to [[{tgt}]]"
    elif act == "delete":
        reason = prm.get("reason", "")
        extra = f"deleted page [[{page}]]{f' ({reason})' if reason else ''}"
    elif act == "create":
        extra = f"created page [[{page}]]"
    elif act == "upload":
        extra = f"uploaded file [[{page}]]"
    else:                            # fall-back: “action TITLE”
        extra = f"{act} [[{page}]]"

    if cmt:
        extra += f" ({cmt})"

    return f"* {ts} {usr} {extra}"

# ─── fetch every log event for one title ───────────────────────────
def full_log(site, title: str) -> str:
    lines, cont = [], None
    while True:
        q = {
            "action": "query", "list": "logevents",
            "letitle": title, "lelimit": "max", "format": "json"
        }
        if cont: q["lecontinue"] = cont
        data = site.api(**q)
        for e in data["query"]["logevents"]:
            lines.append(log_bullet(e))
        cont = data.get("continue", {}).get("lecontinue")
        if not cont:
            break
    return "\n".join(lines)

# ─── utilities ─────────────────────────────────────────────────────
def load_titles() -> list[str]:
    if not os.path.exists(PAGES_TXT):
        sys.exit("pages.txt not found")
    with open(PAGES_TXT, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.startswith("Category:")]

def wiki_site() -> mwclient.Site:
    u = urllib.parse.urlparse(API_URL)
    return mwclient.Site(u.netloc, path=u.path.rsplit("/api.php",1)[0]+"/")

# ─── main loop ─────────────────────────────────────────────────────
def main():
    site = wiki_site()
    site.login(USERNAME, PASSWORD)

    for n, title in enumerate(load_titles(), 1):
        print(f"{n:>3} ▶︎ {title}")
        pg = site.pages[title]
        if not pg.exists:
            print("    • missing – skip"); continue

        # read current text & normalise first line if needed
        lines = pg.text().splitlines()
        if lines and ADD_RX.match(lines[0]):
            lines[0] = ADD_RX.sub(r"[[Category:\1]]", lines[0])
        body = "\n".join(lines).rstrip()

        log_block = full_log(site, title)
        if not log_block:
            print("    • no log – skip"); continue

        new = (
            "ACTUAL LOG\n" + log_block + "\n\n"
            "== Old Content ==\n" + body + "\n"
        )
        if "[[Category:Log added categories]]" not in new:
            new += "[[Category:Log added categories]]\n"

        try:
            pg.save(new, summary="Bot: prepend full log & fix header")
            print("    ✓ saved")
        except APIError as e:
            print("    ! save failed:", e.code)
        time.sleep(THROTTLE)

    print("Finished repairing all listed pages.")

if __name__ == "__main__":
    main()
