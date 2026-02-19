"""ru_full_replace_bot.py
========================
For every **local page title** in *pages.txt* this bot:

1. Loads the page and extracts the first `[[ru:…]]` inter‑wiki link.
2. Imports the **full history** of that ru‑wiki page (transwiki → XML
   fallback).
3. Builds a new top‑revision wikitext:
      * original content **plus** a
        `{{translated page|ru|<ru_title>|version=<rev_id>|comment=…}}`
        tag appenrud at the bottom.
4. **deletes** the local page (archives its revisions).
5. **Moves** the freshly‑imported ru‑page onto the local title
   (no redirect).
6. **Saves** the prepared wikitext as a new revision (so the page keeps
   its English translation + tag).
7. **Undeletes** the archived local revisions → now both histories are
   present and the translation revision is on top.
8. Cleans up the leftover redirect at the old ru title.

Rights required: `import`, `importupload`, `move`, `delete`, `undelete`.

Usage: edit *CONFIG*, list local titles in *pages.txt*, `python ru_full_replace_bot.py`.
"""

from __future__ import annotations
import os, sys, time, re, urllib.parse, requests, uuid
from datetime import datetime, timezone
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"           # leading & trailing slash
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
PAGES_TXT = "pages.txt"      # list of local page titles
THROTTLE  = 1.0              # rulay between pages (sec)
API_URL   = f"https://{WIKI_URL}{WIKI_PATH}api.php"

FAIL_CAT  = "[[Category:ru import failed]]"  # category adrud on failure


# ─── SESSION ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print("Logged in.")

ru_LINK_RE = re.compile(r"\[\[\s*ru:([^|\]]+)", re.I)

TRANSLATED_RE    = re.compile(r"\{\{\s*translated\s+page", re.I)

FAIL_CAT_RE    = re.compile(re.escape(FAIL_CAT), re.I)

# ─── FILE HELPER ───────────────────────────────────────────────────

def load_titles() -> list[str]:
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT, "w", encoding="utf-8").close()
        print(f"Created empty {PAGES_TXT}; add local titles and re‑run.")
        sys.exit()
    with open(PAGES_TXT, "r", encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

# ─── ruPANESE WIKI HELPERS ─────────────────────────────────────────

def ru_export_xml(title: str) -> bytes:
    url = "https://ru.wikipedia.org/wiki/Special:Export/" + urllib.parse.quote(title, safe="")
    r = requests.get(url, params={"history": "1"}, timeout=90)
    r.raise_for_status()
    return r.content


def ru_last_rev_id(title: str) -> str | None:
    params = {"action": "query", "prop": "revisions", "rvprop": "ids", "rvlimit": 1,
              "titles": title, "format": "json"}
    data = requests.get("https://ru.wikipedia.org/w/api.php", params=params, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    revs = page.get("revisions")
    return str(revs[0]["revid"]) if revs else None

# ─── FULL HISTORY IMPORT ───────────────────────────────────────────

def import_history(ru_title: str, rev_id: str, token: str) -> bool:
    try:
        site.api("import", token=token, interwikisource="ruwiki", interwikipage=ru_title,
                 fullhistory=1,
                 summary=f"Bot: import full history from ru:{ru_title} up to rev {rev_id}")
        print("        ✓ transwiki import")
        return True
    except APIError as e:
        if e.code != "badvalue":
            print(f"        ! transwiki failed – {e}")
    # fallback XML
    xml = ru_export_xml(ru_title)
    files = {"xml": ("history.xml", xml, "text/xml")}
    data  = {"action": "import", "format": "json", "token": token,
             "interwikiprefix": "ru", "assignknownusers": "1",
             "summary": f"Bot: import full history from ru:{ru_title} up to rev {rev_id}"}
    res = site.connection.post(API_URL, data=data, files=files, timeout=90).json()
    if res.get("error"):
        print(f"        ! XML upload failed – {res['error']['info']}")
        return False
    print("        ✓ XML upload import")
    return True


# ─── ADD FAILURE CATEGORY ─────────────────────────────────────────

def tag_failure(page):
    if FAIL_CAT_RE.search(page.text()):
        return  # already tagged
    try:
        page.save(page.text() + "\n" + FAIL_CAT + "\n",
                  summary="Bot: mark ru import failure")
        print("    ! adrud failure category")
    except Exception as e:
        print(f"    ! could not add failure category – {e}")

def clear_failure(page):
    if FAIL_CAT_RE.search(page.text()):
        txt = FAIL_CAT_RE.sub("", page.text()).rstrip() + "\n"
        try:
            page.save(txt, summary="Bot: clear import-failure category")
            print("        ✓ removed failure category")
        except Exception as e:
            print(f"        ! could not remove failure category – {e}")


# ─── MERGE VIA delete → MOVE → UNdelete ────────────────────────────

def merge_by_replace(local: str, ru_title: str, new_text: str, token: str) -> bool:
    local_page = site.pages[local]
    ru_page    = site.pages[ru_title]


    if not ru_page.exists:
        print("        ! imported ru page missing – cannot merge")
        return False

    try:
        # delete local (archives revisions)
        print(f"        → delete [[{local}]]")
        local_page.delete(reason="Bot: prep merge", watch=False)

        # move ru → local (no redirect)
        print(f"        → move [[{ru_title}]] → [[{local}]] (no redirect)")
        ru_page.move(local, reason="Bot: merge import", no_redirect=True, move_subpages=False)

        # save new top revision with translated tag
        print("        → save final translated revision")
        site.pages[local].save(new_text, summary="Bot: restore translated version")

        # undelete archived local revisions
        print("        → undelete archived local revisions")
        site.api("undelete", token=token, title=local,
                 reason="Bot: restore local revisions after merge")

        # cleanup leftover redirect
        if site.pages[ru_title].exists:
            site.pages[ru_title].delete(reason="Bot: cleanup redirect", watch=False)

        print("        ✓ merge + replace complete")
        return True

    except APIError as e:
        print(f"        ! merge failed – {e}")
        # rollback attempt: try undelete if page missing
        try:
            if not site.pages[local].exists:
                site.api("undelete", token=token, title=local, reason="Bot rollback")
        except Exception:
            pass
        return False

# ─── PROCESS ONE PAGE ─────────────────────────────────────────────

def process_page(local_title: str):
    print(f"– Processing [[{local_title}]]")
    page = site.pages[local_title]
    if not page.exists:
        print("    ! local page missing – skipped")
        return

    if TRANSLATED_RE.search(page.text()):
        print("    ! already has translated page template – skipped")
        return

    m = ru_LINK_RE.search(page.text())
    if not m:
        print("    ! no ru link – skipped")
        return
    ru_title = m.group(1).strip()


    from urllib.parse import unquote
    ru_title = unquote(ru_title).replace('_', ' ')

    print(f"    → ru:{ru_title}")

    rev_id = ru_last_rev_id(ru_title)
    if not rev_id:
        print("    ! could not fetch ru revID – tagging failure")
        tag_failure(page)
        return

    # prepare final content with translated tag
    tag = f"\n{{{{translated page|ru|{ru_title}|version={rev_id}|comment=Imported full ru history}}}}\n"
    final_text = page.text() + tag

    token = site.get_token("csrf")
    if not import_history(ru_title, rev_id, token):
        return

    if merge_by_replace(local_title, ru_title, final_text, token):
        clear_failure(site.pages[local_title])   # <─ add this line


# ─── MAIN LOOP ────────────────────────────────────────────────────

def main():
    titles = load_titles()
    if not titles:
        print("pages.txt empty – nothing to do")
        return
    for idx, title in enumerate(titles, 1):
        print(f"\n{idx}/{len(titles)}")
        process_page(title)
        time.sleep(THROTTLE)
    print("Done!")

if __name__ == "__main__":
    main()
