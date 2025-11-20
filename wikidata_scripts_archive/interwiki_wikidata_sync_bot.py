#!/usr/bin/env python3
"""
interwiki_wikidata_sync_bot.py  –  append Wikidata-derived interwiki blocks
-------------------------------------------------------------------------
For every page supplied in *pages.txt* this bot:
  1. Scans the pageʼs wikitext for the **first** {{ja:…}}, {{de:…}},
     {{zh:…}} and {{en:…}} inter-wiki link.
  2. Looks up that articleʼs *Wikidata* item and fetches **all** its
     sitelinks.
  3. Writes four comment-delimited blocks **at the bottom** of the page,
     always in the fixed order ↓

        <!--jawiki derived wikidata interwikis-->
        …links…
        <!--dewiki derived wikidata interwikis-->
        …links…
        <!--zhwiki derived wikidata interwikis-->
        …links…
        <!--enwiki derived wikidata interwikis-->
        …links…

     *Each* block is appended only if at least one of its links is not
     already present; nothing is overwritten.
  4. "commonswiki" sitelinks are output as

        {{Commons category|PAGE}}

Requirements
------------
* `mwclient` (MediaWiki API wrapper)
* `requests`  (HTTP requests)

Adapt the CONFIG section as needed (URL, credentials, throttle, …).
"""

import os, sys, time, re, urllib.parse, requests, mwclient
from typing import Dict, List, Optional

# ─── CONFIG ───────────────────────────────────────────────────────────
SHINTO_URL  = "shinto.miraheze.org"
SHINTO_PATH = "/w/"

USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"          # ⇐ change / use env-var / keyring

PAGES_FILE = "pages.txt"
THROTTLE    = 0.1            # seconds between API writes
WD_API      = "https://www.wikidata.org/w/api.php"

# ─── MW SESSIONS ──────────────────────────────────────────────────────
print(f"Connecting to {SHINTO_URL} …")
site_local = mwclient.Site(SHINTO_URL, path=SHINTO_PATH)
site_local.login(USERNAME, PASSWORD)
print("  ↳ logged in ✔")

# read-only language wikis – only used for *one* API call each
LANG_SITES = {
    "ja": mwclient.Site("ja.wikipedia.org", path="/w/"),
    "de": mwclient.Site("de.wikipedia.org", path="/w/"),
    "zh": mwclient.Site("zh.wikipedia.org", path="/w/"),
    "en": mwclient.Site("en.wikipedia.org", path="/w/"),
}

# ─── REGEXES ──────────────────────────────────────────────────────────
IW_RE = re.compile(r"\[\[\s*(ja|de|zh|en)\s*:\s*([^\]|]+)")
COMMONS_TMPL = "{{Commons category|%s}}"

# ─── HELPERS ──────────────────────────────────────────────────────────

def load_titles(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def first_lang_link(text: str, code: str) -> Optional[str]:
    """Return the *first* linked title for a given language code."""
    for m in IW_RE.finditer(text):
        if m.group(1).lower() == code:
            return urllib.parse.unquote(m.group(2)).replace("_", " ")
    return None


def lang_article_qid(code: str, title: str) -> Optional[str]:
    """Return the Wikidata Q-id for *title* on <code>wiki>"""
    lang_site = LANG_SITES[code]
    data = lang_site.api(
        action="query", format="json",
        prop="pageprops", titles=title, ppprop="wikibase_item"
    )
    props = next(iter(data["query"]["pages"].values())).get("pageprops", {})
    return props.get("wikibase_item")


def wd_sitelinks(qid: str) -> Dict[str, str]:
    if not qid:
        return {}
    j = requests.get(
        WD_API,
        params={
            "action": "wbgetentities",
            "format": "json",
            "ids": qid,
            "props": "sitelinks",
        },
        timeout=30,
    ).json()
    sl = j.get("entities", {}).get(qid, {}).get("sitelinks", {})
    # return e.g. {"en": "Foo", "commons": "Bar"}
    out: Dict[str, str] = {}
    for key, info in sl.items():
        if key.endswith("wiki"):
            lang = key[:-4]  # drop "wiki"
            out[lang] = info["title"].split(":", 1)[-1]
    if "commons" in sl:  # handled separately
        out["commons"] = sl["commons"]["title"]
    return out


REDUNDANT_COMMENT_RE = re.compile(r"<!--[a-z]+wiki derived wikidata interwikis-->", re.I)


def append_if_missing(page, lines: List[str], summary: str):
    """Append *lines* to *page* if they are missing."""
    try:
        txt = page.text()
    except Exception as e:
        print(f"    ! cannot read {page.name}: {e}")
        return

    # avoid duplicating comment headers as well as link lines
    missing = [ln for ln in lines if ln not in txt]
    if not missing:
        return

    new_txt = txt.rstrip() + "\n" + "\n".join(missing) + "\n"
    try:
        page.save(new_txt, summary=summary)
        print(f"      · appended {len(missing)} line(s)")
    except mwclient.errors.APIError as e:
        print(f"    ! save failed for {page.name}: {e.code}")


# ─── MAIN LOGIC ──────────────────────────────────────────────────────

def process_page(title: str):
    pg = site_local.pages[title]
    if not pg.exists:
        print("  ! page missing – skipped")
        return

    text = pg.text()
    blocks: List[str] = []  # lines to maybe append later

    for lang in ("ja", "de", "zh", "en"):
        art_title = first_lang_link(text, lang)
        if not art_title:
            continue  # no link for this language

        print(f"    · {lang}wiki link → {art_title}")
        qid = lang_article_qid(lang, art_title)
        if not qid:
            print("      ↳ no Wikidata item – skipped")
            continue

        sitelinks = wd_sitelinks(qid)
        if not sitelinks:
            print("      ↳ no sitelinks")
            continue

        header = f"<!--{lang}wiki derived wikidata interwikis-->"
        block_lines = [header]

        for sl_lang, sl_title in sorted(sitelinks.items()):
            if sl_lang == "commons":
                block_lines.append(COMMONS_TMPL % sl_title)
            else:
                block_lines.append(f"[[{sl_lang}:{sl_title}]]")

        blocks.extend(block_lines)

    if blocks:
        append_if_missing(pg, blocks, "Bot: append Wikidata-derived interwikis")
    else:
        print("    · no new interwikis to add")


def main():
    titles = load_titles(PAGES_FILE)
    for idx, t in enumerate(titles, 1):
        print(f"\n{idx}/{len(titles)} → [[{t}]]")
        process_page(t)
        time.sleep(THROTTLE)

    print("\nDone.")


if __name__ == "__main__":
    main()
