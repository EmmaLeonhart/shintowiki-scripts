#!/usr/bin/env python3
"""
template_sync_or_cleanup.py  –  EN-wiki redirect synchroniser (v2)
=================================================================

* Walk the entire **Template:** namespace (NS 10).
* If a template is **not transcluded anywhere** → delete it.
* If its first non-blank line is a redirect to an English-Wikipedia template
  (`#redirect [[en:Template:Foo]]` or `#redirect [[:en:Template:Foo]]`):
    1. Query enwiki – if the target is missing → delete local template.
    2. Otherwise fetch raw wikitext from enwiki, overwrite local template
       with that content (summary: *Bot: sync with enwiki*).
    3. Scan that wikitext for transcluded templates; for each valid title
       that doesn’t yet exist locally, import its raw content from enwiki
       (summary: *Bot: import from enwiki*).
* Titles containing illegal characters (e.g., “<” or “{”) are ignored.

Requires delete/undelete rights and `mwclient`.
"""
import re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "template-sync-bot/2.0 (User:Immanuelle)"}

REDIRECT_RE  = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):\s*Template:([^\]|]+)", re.I)
INCLUDE_RE   = re.compile(r"\{\{\s*(?:[Tt]emplate:)?\s*([^\|{}\n]+)", re.I)
VALID_TITLE  = re.compile(r"^[A-Za-z0-9_ \-]+$")  # simple title whitelist

# ─── EN-WIKI HELPERS ───────────────────────────────────────────────

def enwiki_raw(title: str) -> str | None:
    """Return raw wikitext of Template:title from enwiki or None if missing."""
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "titles": f"Template:{title}", "formatversion": "2",
        "format": "json"
    }
    r = requests.get(EN_API, params=params, headers=UA, timeout=10)
    r.raise_for_status()
    page = r.json()["query"]["pages"][0]
    if "missing" in page:
        return None
    return page["revisions"][0]["slots"]["main"]["content"]

# ─── LOCAL ACTIONS ─────────────────────────────────────────────────

def delete_page(page: mwclient.page, reason: str):
    try:
        page.delete(reason=reason, watch=False)
        print("    • deleted", page.name)
    except APIError as e:
        print("    ! delete failed:", e.code)


def save_page(page: mwclient.page, text: str, summary: str):
    try:
        page.save(text, summary=summary)
        print("    • saved", page.name)
    except APIError as e:
        print("    ! save failed:", e.code)

# ─── MAIN PROCESSOR ───────────────────────────────────────────────

def main():
    site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
    site.login(USERNAME, PASSWORD)

    cont = None
    while True:
        params = {
            "action": "query", "list": "allpages", "apnamespace": 10,
            "aplimit": "max", "format": "json"
        }
        if cont:
            params["apcontinue"] = cont
        batch = site.api(**params)
        for ap in batch["query"]["allpages"]:
            title = ap["title"]  # Template:Foo
            tpl = site.pages[title]
            text = tpl.text()
            print("→", title)

            # 1. delete if unused
            ei = site.api(action='query', list='embeddedin', eititle=title,
                          eilimit='1', format='json')["query"]["embeddedin"]
            if not ei:
                delete_page(tpl, "Bot: delete unused template")
                time.sleep(THROTTLE)
                continue

            # 2. handle en-wiki redirect
            first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            m = REDIRECT_RE.match(first_line)
            if not m:
                continue  # not a redirect to en

            en_target = urllib.parse.unquote(m.group(1)).replace('_', ' ')
            raw = enwiki_raw(en_target)
            if raw is None:
                print("  • enwiki target missing – deleting template")
                delete_page(tpl, "Bot: dead enwiki redirect")
                time.sleep(THROTTLE)
                continue

            save_page(tpl, raw, "Bot: sync with enwiki")
            time.sleep(THROTTLE)

            # import sub-templates (single level)
            for name in {urllib.parse.unquote(n).strip() for n in INCLUDE_RE.findall(raw)}:
                if (name.startswith("#") or name.startswith("!") or
                        not VALID_TITLE.match(name)):
                    continue
                local_inc = site.pages[f"Template:{name}"]
                if local_inc.exists:
                    continue
                src = enwiki_raw(name)
                if src is None:
                    continue
                save_page(local_inc, src, "Bot: import from enwiki")
                time.sleep(THROTTLE)

        if 'continue' in batch:
            cont = batch['continue']['apcontinue']
        else:
            break
    print("Finished template sync/cleanup.")

if __name__ == '__main__':
    main()