#!/usr/bin/env python3
"""
split_erroneous_history_bot.py  (move + XML import with retries)
================================================================
For every page in pages.txt:

 1. Move → Title-ERROR (no redirect)
 2. Tag Title-ERROR with [[Category:deleted revision storage]]
 3. Keep only revisions ≥ the first post-2020 edit by “Immanuelle”
 4. Build an XML export of just those revisions (with <comment>)
 5. Import that XML back to the original title (including templates)

On network/API failure, it retries the import up to 3× and then skips on error.
"""

import os, sys, time, io
from xml.sax.saxutils import escape

import mwclient
from mwclient.errors import APIError
import requests
from requests.exceptions import RequestException

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL    = "shinto.miraheze.org"
WIKI_PATH   = "/w/"
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_2]"
PAGES_FILE  = "pages.txt"
THROTTLE    = 1.0     # seconds between heavy actions
CUTOFF_TS   = "2020-01-01T00:00:00Z"
ERROR_CAT   = "[[Category:deleted revision storage]]"
MAX_RETRIES = 3

# ─── LOGIN ─────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")
API_URL = f"https://{WIKI_URL}{WIKI_PATH}api.php"

# ─── HELPERS ───────────────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def fetch_all_revs(title):
    """Return list (oldest→newest) of dicts {revid, timestamp, user, comment, slots}."""
    revs = []
    params = {
        "action":  "query",
        "format":  "json",
        "prop":    "revisions",
        "titles":  title,
        "rvprop":  "ids|timestamp|user|comment|content",
        "rvslots": "main",
        "rvlimit": "max",
        "rvdir":   "newer",
    }
    while True:
        data = site.api(**params)
        page = next(iter(data["query"]["pages"].values()))
        revs.extend(page.get("revisions", []))
        cont = data.get("continue", {}).get("rvcontinue")
        if not cont:
            break
        params["rvcontinue"] = cont
    return revs

def first_good_rev_id(revs):
    """First revid whose timestamp≥CUTOFF_TS and user contains “Immanuelle”."""
    for r in revs:
        if r["timestamp"] >= CUTOFF_TS and "Immanuelle" in r["user"]:
            return r["revid"]
    return None

def build_xml(title, kept):
    """Build minimal mediawiki XML (with <comment>) for kept revisions."""
    parts = [
        '<?xml version="1.0"?>',
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/" '
          'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
          'xsi:schemaLocation="http://www.mediawiki.org/xml/export-0.11/ '
          'http://www.mediawiki.org/xml/export-0.11.xsd" '
          'version="0.11" xml:lang="en">',
        '  <siteinfo><sitename>Shinto Wiki</sitename><dbname>shintowiki</dbname></siteinfo>',
        f'  <page><title>{escape(title)}</title>'
    ]
    fid = 1
    for r in kept:
        ts      = escape(r["timestamp"])
        user    = escape(r["user"])
        comment = escape(r.get("comment",""))
        text    = escape(r["slots"]["main"]["*"])
        parts += [
            "    <revision>",
            f"      <id>{fid}</id>",
            f"      <timestamp>{ts}</timestamp>",
            f"      <contributor><username>{user}</username></contributor>",
            f"      <comment>{comment}</comment>",
            "      <model>wikitext</model><format>text/x-wiki</format>",
            f"      <text xml:space=\"preserve\">{text}</text>",
            "    </revision>",
        ]
        fid += 1
    parts.append("  </page></mediawiki>")
    return "\n".join(parts).encode("utf-8")

def ensure_error_cat(page):
    txt = page.text()
    if ERROR_CAT not in txt:
        page.save(
            txt.rstrip() + "\n" + ERROR_CAT + "\n",
            summary="Bot: mark deleted revision storage"
        )

# ─── SPLIT & REIMPORT ───────────────────────────────────────────────
def split_page(title):
    pg = site.pages[title]
    if not pg.exists:
        print(f"  ! [[{title}]] missing, skipping")
        return

    revs = fetch_all_revs(title)
    cut  = first_good_rev_id(revs)
    if not cut:
        print("  ! no qualifying Immanuelle edit, skipping")
        return

    kept = [r for r in revs if r["revid"] >= cut]
    if not kept:
        print("  ! nothing to keep, skipping")
        return

    err = f"{title}-ERROR"
    try:
        pg.move(err, reason="Bot: store suspect history", no_redirect=True)
        print(f"  • Moved to [[{err}]]")
    except APIError as e:
        print(f"  ! move failed: {e.code}")
        return

    ensure_error_cat(site.pages[err])
    time.sleep(THROTTLE)

    xml_bytes = build_xml(title, kept)
    files = {"xml": ("import.xml", io.BytesIO(xml_bytes), "text/xml")}
    data = {
        "action":           "import",
        "format":           "json",
        "token":            site.get_token("csrf"),
        "summary":          "Bot: restore post-2020 Immanuelle history",
        "interwikiprefix":  "local",   # required non-empty
        "assignknownusers": "1",
        "templates":        "1",       # pull in all transcluded templates
    }

    for attempt in range(1, MAX_RETRIES+1):
        try:
            res = site.connection.post(API_URL, data=data, files=files, timeout=120).json()
        except RequestException as e:
            print(f"    ! Import attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(THROTTLE)
                continue
            else:
                print("    ! All import attempts failed, skipping")
                return
        if "error" in res:
            errc = res["error"].get("code")
            info = res["error"].get("info")
            print(f"    ! Import API error [{errc}]: {info}")
            return
        print(f"    ✓ Imported {len(kept)} revisions back to [[{title}]]")
        return

# ─── MAIN LOOP ───────────────────────────────────────────────────────
def main():
    titles = load_titles(PAGES_FILE)
    for i,t in enumerate(titles,1):
        print(f"\n{i}/{len(titles)}: [[{t}]]")
        try:
            split_page(t)
        except Exception as e:
            print(f"  ! unexpected error on [[{t}]]: {e}")
        time.sleep(THROTTLE)
    print("\nDone.")

if __name__ == "__main__":
    main()
