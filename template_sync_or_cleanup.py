#!/usr/bin/env python3
"""
template_sync_or_cleanup.py
===========================

Iterate over every page in the **Template:** namespace (NS 10).

• If a template isn’t transcluded anywhere (no `embeddedin` entries) – delete it.
• If the first non-blank line matches
     `#redirect [[en:Template:Name]]` or `#redirect [[:en:Template:Name]]`
  then:
    1. Check via the enwiki API whether Template:Name exists.
    2. If it **doesn’t** exist – delete the local template.
    3. If it **does** – fetch its full wikitext and replace the local page
       with that content (edit summary “Bot: sync with enwiki”).
    4. Scan the fetched wikitext for `{{Template| … }}` transclusions; for
       each template that doesn’t yet exist locally, fetch the raw content
       from enwiki and create it locally (tagging: “Bot: import from enwiki”).

Requires admin rights (delete) and write rights.
"""
import os, re, sys, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "template-sync-bot/1.0 (User:Immanuelle)"}

REDIR_RE = re.compile(r"^#redirect\s*\[\[\s*:?(?:en):\s*Template:([^\]|]+)", re.I)
INCLUDE_RE = re.compile(r"\{\{\s*([Tt]emplate:)?\s*([^\|{}\n]+)", re.I)

# ─── ENWIKI API HELPERS ────────────────────────────────────────────

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

# ─── LOCAL SITE UTILS ──────────────────────────────────────────────

def delete_page(page, reason):
    try:
        page.delete(reason=reason, watch=False)
        print("    • deleted", page.name)
    except APIError as e:
        print("    ! delete failed", e.code)

# ─── MAIN LOGIC ────────────────────────────────────────────────────

def main():
    site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
    site.login(USERNAME, PASSWORD)

    apc = None
    while True:
        ap = {
            "action": "query", "list": "allpages", "apnamespace": 10,
            "aplimit": "max", "format": "json"
        }
        if apc:
            ap["apcontinue"] = apc
        data = site.api(**ap)
        for pg in data["query"]["allpages"]:
            title = pg["title"]  # Template:Foo
            t_name = title.split(":",1)[1]
            tpl = site.pages[title]
            txt = tpl.text() if tpl.exists else ""
            print("→", title)

            # --- check transclusions ---
            ei = site.api(action='query', list='embeddedin', einamespace='0|2|4|6|14',
                          eititle=title, eilimit='1', format='json')['query']['embeddedin']
            if not ei:  # not transcluded anywhere
                delete_page(tpl, "Bot: delete unused template")
                time.sleep(THROTTLE)
                continue

            # --- redirect handling ---
            first = next((ln.strip() for ln in txt.splitlines() if ln.strip()), "")
            m = REDIR_RE.match(first)
            if not m:
                continue  # not a redirect to enwiki
            en_target = urllib.parse.unquote(m.group(1)).replace('_',' ')
            raw = enwiki_raw(en_target)
            if raw is None:
                print("  • enwiki target missing – delete")
                delete_page(tpl, "Bot: dead enwiki redirect")
                time.sleep(THROTTLE)
                continue

            # replace content with enwiki raw text
            try:
                tpl.save(raw, summary="Bot: sync with enwiki")
                print("  ✓ synced content")
            except APIError as e:
                print("  ! save failed", e.code)
                continue
            time.sleep(THROTTLE)

            # import sub-templates recursively (1 level)
            for inc in INCLUDE_RE.findall(raw):
                name = urllib.parse.unquote(inc[1]).strip()
                # ignore variables / parser-functions
                if name.startswith("#") or name.startswith("!"):
                    continue
                local_inc = site.pages[f"Template:{name}"]
                if local_inc.exists:
                    continue
                raw_inc = enwiki_raw(name)
                if raw_inc is None:
                    continue
                try:
                    local_inc.save(raw_inc, summary="Bot: import from enwiki")
                    print("    • imported Template:", name)
                except APIError as e:
                    print("    ! failed import", name, e.code)
                time.sleep(THROTTLE)
        if 'continue' in data:
            apc = data['continue']['apcontinue']
        else:
            break
    print("Finished.")

if __name__ == '__main__':
    main()