"""de_full_replace_bot.py
========================
For every **local page title** in *pages.txt* this bot:

1. Loads the page and extracts the first `[[de:…]]` inter‑wiki link.
2. Imports the **full history** of that de‑wiki page (transwiki → XML
   fallback).
3. Builds a new top‑revision wikitext:
      * original content **plus** a
        `{{translated page|de|<de_title>|version=<rev_id>|comment=…}}`
        tag appended at the bottom.
4. **Deletes** the local page (archives its revisions).
5. **Moves** the freshly‑imported de‑page onto the local title
   (no redirect).
6. **Saves** the prepared wikitext as a new revision (so the page keeps
   its English translation + tag).
7. **Undeletes** the archived local revisions → now both histories are
   present and the translation revision is on top.
8. Cleans up the leftover redirect at the old de title.

Rights required: `import`, `importupload`, `move`, `delete`, `undelete`.

Usage: edit *CONFIG*, list local titles in *pages.txt*, `python de_full_replace_bot.py`.
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
THROTTLE  = 1.0              # delay between pages (sec)
API_URL   = f"https://{WIKI_URL}{WIKI_PATH}api.php"

FAIL_CAT  = "[[Category:de import failed]]"  # category added on failure


# ─── SESSION ───────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print("Logged in.")

de_LINK_RE = re.compile(r"\[\[\s*de:([^|\]]+)", re.I)

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

# ─── dePANESE WIKI HELPERS ─────────────────────────────────────────

def de_export_xml(title: str) -> bytes:
    url = "https://de.wikipedia.org/wiki/Special:Export/" + urllib.parse.quote(title, safe="")
    r = requests.get(url, params={"history": "1"}, timeout=90)
    r.raise_for_status()
    return r.content


def de_last_rev_id(title: str) -> str | None:
    params = {"action": "query", "prop": "revisions", "rvprop": "ids", "rvlimit": 1,
              "titles": title, "format": "json"}
    data = requests.get("https://de.wikipedia.org/w/api.php", params=params, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    revs = page.get("revisions")
    return str(revs[0]["revid"]) if revs else None

# ─── FULL HISTORY IMPORT ───────────────────────────────────────────

def import_history(de_title: str, rev_id: str, token: str) -> bool:
    try:
        site.api("import", token=token, interwikisource="dewiki", interwikipage=de_title,
                 fullhistory=1,
                 summary=f"Bot: import full history from de:{de_title} up to rev {rev_id}")
        print("        ✓ transwiki import")
        return True
    except APIError as e:
        if e.code != "badvalue":
            print(f"        ! transwiki failed – {e}")
    # fallback XML
    xml = de_export_xml(de_title)
    files = {"xml": ("history.xml", xml, "text/xml")}
    data  = {"action": "import", "format": "json", "token": token,
             "interwikiprefix": "de", "assignknownusers": "1",
             "summary": f"Bot: import full history from de:{de_title} up to rev {rev_id}"}
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
                  summary="Bot: mark de import failure")
        print("    ! added failure category")
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


# ─── MERGE VIA DELETE → MOVE → UNDELETE ────────────────────────────

def merge_by_replace(local: str, de_title: str, new_text: str, token: str) -> bool:
    local_page = site.pages[local]
    de_page    = site.pages[de_title]


    if not de_page.exists:
        print("        ! imported de page missing – cannot merge")
        return False

    try:
        # delete local (archives revisions)
        print(f"        → delete [[{local}]]")
        local_page.delete(reason="Bot: prep merge", watch=False)

        # move de → local (no redirect)
        print(f"        → move [[{de_title}]] → [[{local}]] (no redirect)")
        de_page.move(local, reason="Bot: merge import", no_redirect=True, move_subpages=False)

        # save new top revision with translated tag
        print("        → save final translated revision")
        site.pages[local].save(new_text, summary="Bot: restore translated version")

        # undelete archived local revisions
        print("        → undelete archived local revisions")
        site.api("undelete", token=token, title=local,
                 reason="Bot: restore local revisions after merge")

        # cleanup leftover redirect
        if site.pages[de_title].exists:
            site.pages[de_title].delete(reason="Bot: cleanup redirect", watch=False)

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

    m = de_LINK_RE.search(page.text())
    if not m:
        print("    ! no de link – skipped")
        return
    de_title = m.group(1).strip()


    from urllib.parse import unquote
    de_title = unquote(de_title).replace('_', ' ')

    print(f"    → de:{de_title}")

    rev_id = de_last_rev_id(de_title)
    if not rev_id:
        print("    ! could not fetch de revID – tagging failure")
        tag_failure(page)
        return

    # prepare final content with translated tag
    tag = f"\n{{{{translated page|de|{de_title}|version={rev_id}|comment=Imported full de history}}}}\n"
    final_text = page.text() + tag

    token = site.get_token("csrf")
    if not import_history(de_title, rev_id, token):
        return

    if merge_by_replace(local_title, de_title, final_text, token):
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
