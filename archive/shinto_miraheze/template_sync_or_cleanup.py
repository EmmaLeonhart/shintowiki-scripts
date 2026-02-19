#!/usr/bin/env python3
"""
template_sync_or_cleanup.py  –  EN-wiki redirect synchroniser (v2.3)
====================================================================

Improvements over v2.1:
• Accept an **optional start-at title** on the command line so you can resume
  from a given template (e.g. `python template_sync_or_cleanup.py Glossary link`).
• `enwiki_raw()` now returns **None** when the API response lacks a
  `revisions` key (was raising KeyError).
"""
import re, time, sys, urllib.parse, requests, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle";         PASSWORD   = "[REDACTED_SECRET_2]"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "template-sync-bot/2.3 (User:Immanuelle)"}

REDIRECT_RE = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):\s*Template:([^\]|]+)", re.I)
INCLUDE_RE  = re.compile(r"\{\{\s*(?:[Tt]emplate:)?\s*([^|{}:\n]+)", re.I)
VALID_TITLE = re.compile(r"^[A-Za-z0-9 _\-]+$")

START_AT = sys.argv[1] if len(sys.argv) > 1 else None
resume_flag = bool(START_AT)

# ─── EN-WIKI HELPER ────────────────────────────────────────────────

def enwiki_raw(title: str) -> str | None:
    params = {
        "action":"query","prop":"revisions","rvprop":"content",
        "rvslots":"main","titles":f"Template:{title}",
        "formatversion":"2","format":"json"
    }
    r = requests.get(EN_API, params=params, headers=UA, timeout=10)
    r.raise_for_status()
    pg = r.json()["query"]["pages"][0]
    if "missing" in pg or "revisions" not in pg:
        return None
    return pg["revisions"][0]["slots"]["main"]["content"]

# ─── LOCAL HELPERS ─────────────────────────────────────────────────

def delete_page(pg, reason):
    try:
        pg.delete(reason=reason, watch=False)
        print("    • deleted", pg.name)
    except APIError as e:
        print("    ! delete failed", e.code)

def save_page(pg, text, summary):
    try:
        pg.save(text, summary=summary)
        print("    • saved", pg.name)
    except APIError as e:
        print("    ! save failed", e.code)

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

            # resume logic
            global resume_flag
            if resume_flag and title < START_AT:
                continue
            resume_flag = False

            tpl  = site.pages[title]
            text = tpl.text()
            print("→", title)

            # delete unused
            used = site.api(action='query', list='embeddedin', eititle=title,
                             eilimit=1, format='json')['query']['embeddedin']
            if not used:
                delete_page(tpl, "Bot: delete unused template")
                time.sleep(THROTTLE)
                continue

            # redirect to enwiki?
            first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            m = REDIRECT_RE.match(first)
            if not m:
                continue

            en_target = urllib.parse.unquote(m.group(1)).replace('_',' ')
            raw = enwiki_raw(en_target)
            if raw is None:
                delete_page(tpl, "Bot: dead enwiki redirect")
                time.sleep(THROTTLE)
                continue

            save_page(tpl, raw, "Bot: sync with enwiki")
            time.sleep(THROTTLE)

            # import first-level sub-templates
            for name in {urllib.parse.unquote(n).strip() for n in INCLUDE_RE.findall(raw)}:
                if (not name or name.startswith(('#','!')) or not VALID_TITLE.match(name)):
                    continue
                try:
                    local_inc = site.pages[f"Template:{name}"]
                except InvalidPageTitle:
                    continue
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