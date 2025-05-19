#!/usr/bin/env python3
"""
template_sync_or_cleanup.py  –  EN‑wiki redirect synchroniser (v2.1)
====================================================================

* Walk the entire **Template:** namespace (NS 10).
* Delete templates that are **not transcluded** anywhere.
* For templates that are pure redirects to `en:Template:Foo`:
    1. If `Template:Foo` is missing on enwiki → delete local template.
    2. Otherwise overwrite local template with the raw enwiki wikitext.
    3. Import every first‑level sub‑template transcluded in that wikitext if
       it doesn’t exist locally (skip invalid titles / parser‑functions).

Skipped sub‑template names:
* empty strings or just `Template:`
* names starting with `#` or `!`
* names containing any characters **outside** `[A‑Z a‑z 0‑9 _‑ ]`

Requires delete rights and mwclient.
"""
import re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "template-sync-bot/2.1 (User:Immanuelle)"}

REDIRECT_RE = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):\s*Template:([^\]|]+)", re.I)
INCLUDE_RE  = re.compile(r"\{\{\s*(?:[Tt]emplate:)?\s*([^\|{}\n]+)", re.I)
VALID_TITLE = re.compile(r"^[A-Za-z0-9 _\-]+$")

# ─── EN‑WIKI HELPER ────────────────────────────────────────────────

def enwiki_raw(title: str) -> str | None:
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "titles": f"Template:{title}", "formatversion": "2",
        "format": "json"
    }
    r = requests.get(EN_API, params=params, headers=UA, timeout=10)
    r.raise_for_status()
    pg = r.json()["query"]["pages"][0]
    if "missing" in pg:
        return None
    return pg["revisions"][0]["slots"]["main"]["content"]

# ─── LOCAL WRAPPERS ────────────────────────────────────────────────

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

# ─── MAIN LOOP ────────────────────────────────────────────────────

def main():
    site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
    site.login(USERNAME, PASSWORD)

    apcontinue = None
    while True:
        batch = site.api(action='query', list='allpages', apnamespace=10,
                         aplimit='max', apcontinue=apcontinue, format='json')
        for entry in batch['query']['allpages']:
            title = entry['title']
            tpl = site.pages[title]
            text = tpl.text()
            print("→", title)

            # delete unused template
            emb = site.api(action='query', list='embeddedin', eititle=title,
                           eilimit=1, format='json')['query']['embeddedin']
            if not emb:
                delete_page(tpl, "Bot: delete unused template")
                time.sleep(THROTTLE)
                continue

            # detect redirect to enwiki
            first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            m = REDIRECT_RE.match(first)
            if not m:
                continue
            en_target = urllib.parse.unquote(m.group(1)).replace('_', ' ')
            raw = enwiki_raw(en_target)
            if raw is None:
                delete_page(tpl, "Bot: dead enwiki redirect")
                time.sleep(THROTTLE)
                continue
            save_page(tpl, raw, "Bot: sync with enwiki")
            time.sleep(THROTTLE)

            # import first‑level sub‑templates
            for name in {urllib.parse.unquote(n).strip() for n in INCLUDE_RE.findall(raw)}:
                if (not name or name.startswith(('#', '!')) or not VALID_TITLE.match(name)):
                    continue
                try:
                    local_inc = site.pages[f"Template:{name}"]
                except InvalidPageTitle:
                    continue  # skip illegal titles
                if local_inc.exists:
                    continue
                src = enwiki_raw(name)
                if src is None:
                    continue
                save_page(local_inc, src, "Bot: import from enwiki")
                time.sleep(THROTTLE)

        if 'continue' in batch:
            apcontinue = batch['continue']['apcontinue']
        else:
            break
    print("Finished template sync/cleanup.")

if __name__ == '__main__':
    main()
