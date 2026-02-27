"""
undo_recent_bot_edits.py
=========================
Undoes all recent edits by User:EmmaBot made after a given timestamp.
Used to roll back a bad bot run.

Edit the CUTOFF timestamp below before running.
"""

import io, sys, time
import os
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "[REDACTED_SECRET_1]")
THROTTLE  = 1.0

# UTC timestamp — undo all edits by this user AT OR AFTER this time
# 2026-02-19 17:06 PST = 2026-02-20 01:06 UTC
CUTOFF = "2026-02-20T01:06:00Z"

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent="UndoBot/1.0 (User:EmmaBot; shinto.miraheze.org)")
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}")
print(f"Undoing all edits at or after {CUTOFF}\n")

# Get recent contributions
contribs = site.api(
    "query",
    list="usercontribs",
    ucuser=USERNAME,
    ucstart=CUTOFF,
    ucdir="newer",
    uclimit=500,
    ucprop="ids|title|timestamp|comment",
)["query"]["usercontribs"]

print(f"Found {len(contribs)} edits to undo\n")

undone = failed = skipped = 0

for edit in contribs:
    title     = edit["title"]
    revid     = edit["revid"]
    parentid  = edit.get("parentid", 0)
    timestamp = edit["timestamp"]
    comment   = edit.get("comment", "")

    print(f"  [{timestamp}] {title}  (rev {revid})")
    print(f"    edit summary: {comment}")

    if parentid == 0:
        # This was a page creation — delete the page instead of undoing
        print(f"    -> Page creation, deleting page")
        try:
            page = site.pages[title]
            if page.exists:
                site.api("delete", title=title,
                         reason="Bot: rolling back bad bot run (page creation)",
                         token=site.get_token("delete"))
                print(f"    DELETED")
                undone += 1
            else:
                print(f"    SKIP (already gone)")
                skipped += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1
    else:
        # Undo the edit
        try:
            result = site.api(
                "edit",
                title=title,
                undo=revid,
                undoafter=parentid,
                summary="Bot: rolling back bad bot run",
                token=site.get_token("edit"),
            )
            print(f"    UNDONE")
            undone += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

    time.sleep(THROTTLE)

print(f"\n{'='*60}")
print(f"Done. Undone: {undone} | Failed: {failed} | Skipped: {skipped}")
