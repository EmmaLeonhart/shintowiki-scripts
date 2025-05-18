#!/usr/bin/env python3
"""
Category Interwiki Restore Bot  –  Tier-2 Category Generator
===========================================================
Creates or confirms **Tier-2 categories** on the local wiki by mining the
parent categories of Commons / jawiki / dewiki categories referenced from the
*Tier-1 pages* listed in `pages.txt`.

Priority for the local category’s **canonical name**
----------------------------------------------------
1. **enwiki** sitelink title
2. **commonswiki** sitelink title
3. **jawiki** sitelink title
4. **dewiki** sitelink title

Workflow per Tier-1 source page
-------------------------------
* Parse page for category inter-wikis: `commons`, `ja`, `de`.
* For each of those remote categories, fetch its **parent categories**.
* For every parent category found, resolve its Wikidata QID.
* For each QID:
  1. Gather sitelinks (enwiki / commonswiki / jawiki / dewiki).
  2. Pick `primary` title by priority above.
  3. Ensure local `Category:primary` exists:
     * **If exists (non-redirect)** → tag `Category:Categories confirmed during Tier 2 run`
     * **Else** create page → tag `Category:Categories created from <source> title`
  4. Append all inter-wiki lines (with comment headers) + QID (via {{Wikidata|Q…}}).
  5. Append `[[Category:Tier 2 Categories]]` unless the page is already tagged Tier-1.
  6. Create redirects for every other sitelink title → canonical category (tag with
     `Category:Tier 2 redirect categories`).

Safety notes
------------
* **Never** modify the Tier-1 source pages.
* **Never** overwrite existing content – only append.
* Edits throttled to avoid API abuse.
"""

# Standard lib
import os, sys, re, time, urllib.parse
from typing import List, Dict, Set

# Third-party
import requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
LOCAL_URL   = "shinto.miraheze.org"  # local wiki to edit
LOCAL_PATH  = "/w/"
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_1]"

PAGES_FILE  = "pages.txt"           # Tier-1 source pages
THROTTLE    = 0.5                   # seconds between edits

WD_API      = "https://www.wikidata.org/w/api.php"
UA          = {"User-Agent": "tier2-category-bot/2.0 (User:Immanuelle)"}

# Remote read-only wikis
REMOTE_SITES = {
    "commons": ("commons.wikimedia.org", "/w/"),
    "ja":      ("ja.wikipedia.org", "/w/"),
    "de":      ("de.wikipedia.org", "/w/"),
}

# Tags
TAG_TIER1          = "Tier 1 Categories"
TAG_TIER2          = "Tier 2 Categories"
TAG_CONFIRMED      = "Categories confirmed during Tier 2 run"
TAG_REDIRECT       = "Tier 2 redirect categories"
TAG_CREATED_FROM   = {
    "en":      "Categories created from enwiki title",
    "commons": "Categories created from commonswiki title",
    "ja":      "Categories created from jawiki title",
    "de":      "Categories created from dewiki title",
}

# Priority order for canonical name
PRIORITY = ["en", "commons", "ja", "de"]

# ─── UTILS ─────────────────────────────────────────────────────────

def load_titles() -> List[str]:
    if not os.path.exists(PAGES_FILE):
        print("Missing pages.txt"); sys.exit(1)
    with open(PAGES_FILE, encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip() and not l.startswith("#")]


def wd_get_sitelinks(qid: str) -> Dict[str, str]:
    r = requests.get(WD_API, params={
        "action": "wbgetentities", "ids": qid,
        "props": "sitelinks", "format": "json"
    }, headers=UA, timeout=15)
    ent = r.json().get("entities", {}).get(qid, {})
    sl = {}
    for code, info in ent.get("sitelinks", {}).items():
        lang = code.replace("wiki", "") if code.endswith("wiki") else code
        if lang in ("en", "ja", "de", "commons"):
            sl[lang] = info["title"].split(":",1)[-1]
    return sl


def commons_parent_cats(com_site, title: str) -> List[str]:
    data = com_site.api(action="query", prop="categories", clshow="!hidden",
                        titles=f"Category:{title}", cllimit="max", format="json")
    pg = next(iter(data["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in pg.get("categories", [])]


def wiki_parent_cats(site, title: str) -> List[str]:
    data = site.api(action="query", prop="categories", clshow="!hidden",
                    titles=f"Category:{title}", cllimit="max", format="json")
    pg = next(iter(data["query"]["pages"].values()))
    return [c["title"].split(":",1)[1] for c in pg.get("categories", [])]


def page_qid(site, cat_title: str) -> str | None:
    rv = site.api(action="query", titles=f"Category:{cat_title}", prop="pageprops",
                  ppprop="wikibase_item", format="json")
    return next(iter(rv["query"]["pages"].values()))\
           .get("pageprops", {})\
           .get("wikibase_item")

# ─── LOCAL CATEGORY HELPERS ────────────────────────────────────────

def local_redirect_target(local_site, name: str) -> str | None:
    pg = local_site.pages[f"Category:{name}"]
    if not pg.exists:
        return None
    m = re.match(r"#redirect\s*\[\[Category:([^\]]+)\]\]", pg.text(), re.I)
    return m.group(1) if m else None


def append_lines_to_page(page, text: str, lines: List[str]):
    if not lines:
        return
    new = text.rstrip() + "\n" + "\n".join(lines) + "\n"
    try:
        page.save(new, summary="Bot: sync Tier-2 category")
        print(f"    • saved {page.name}")
    except APIError as e:
        print(f"    ! save failed: {e.code}")

# ─── MAIN ──────────────────────────────────────────────────────────

def main():
    # local session
    local = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
    local.login(USERNAME, PASSWORD)

    # remote read-only sessions
    remote = {code: mwclient.Site(url, path=path) for code,(url,path) in REMOTE_SITES.items()}

    tier1_pages = load_titles()

    for idx, source in enumerate(tier1_pages, 1):
        print(f"\n{idx}/{len(tier1_pages)} ▶ {source}")
        src_page = local.pages[source]
        if not src_page.exists:
            print("  • missing – skipped"); continue
        src_text = src_page.text()

        # ----- gather linked remote categories -----
        commons_links = re.findall(r"\{\{\s*Commons[ _]category\s*\|\s*([^}|]+)", src_text, re.I)
        commons_links += re.findall(r"\[\[\s*commons:Category:([^]|]+)", src_text, re.I)
        ja_links  = re.findall(r"\[\[ja:Category:([^]|]+)", src_text, re.I)
        de_links  = re.findall(r"\[\[de:Category:([^]|]+)", src_text, re.I)

        # Step 1: fetch parent categories for each link -> QIDs
        qids_seen: Set[str] = set()
        parent_qids: Dict[str, Dict[str,str]] = {}  # qid -> sitelinks

        def handle_remote(cat_title: str, code: str):
            qid = page_qid(remote[code], cat_title)
            if not qid or qid in qids_seen:
                return
            qids_seen.add(qid)
            parent_qids[qid] = wd_get_sitelinks(qid)

            # record sitelinks on the remote page too
            parents = commons_parent_cats(remote[code], cat_title) if code == 'commons' else wiki_parent_cats(remote[code], cat_title)
            for p in parents:
                pqid = page_qid(remote[code], p)
                if pqid and pqid not in qids_seen:
                    qids_seen.add(pqid)
                    parent_qids[pqid] = wd_get_sitelinks(pqid)

        for c in commons_links:
            handle_remote(c, 'commons')
        for j in ja_links:
            handle_remote(j, 'ja')
        for d in de_links:
            handle_remote(d, 'de')

        # ----- create/confirm local categories for each QID -----
        for qid, sitelinks in parent_qids.items():
            # choose canonical
            chosen_lang = next((l for l in PRIORITY if l in sitelinks), None)
            if not chosen_lang:
                continue
            chosen_title = urllib.parse.unquote(sitelinks[chosen_lang]).replace('_',' ')
            tgt = local_redirect_target(local, chosen_title) or chosen_title
            cat_page = local.pages[f"Category:{tgt}"]
            exists = cat_page.exists and not cat_page.redirect
            original_text = cat_page.text() if exists else ""
            add_lines: List[str] = []

            # tagging
            tag_line = f"[[Category:{TAG_CONFIRMED}]]" if exists else f"[[Category:{TAG_CREATED_FROM[chosen_lang]}]]"
            if tag_line not in original_text:
                add_lines.append(tag_line)
            # QID template
            qid_line = f"{{{{Wikidata|{qid}}}}}"
            if qid_line not in original_text:
                add_lines.append(qid_line)
            # interwiki lines
            def iw_line(lang, title):
                if lang == 'en': return f"<!--enwiki derived-->\n[[en:Category:{title}]]"
                if lang == 'commons': return f"<!--commons derived-->\n{{{{Commons category|{title}}}}}"
                if lang == 'ja': return f"<!--jawiki derived-->\n[[ja:Category:{title}]]"
                return f"<!--dewiki derived-->\n[[de:Category:{title}]]"
            for lang in PRIORITY:
                if lang in sitelinks:
                    line = iw_line(lang, urllib.parse.unquote(sitelinks[lang]).replace('_',' '))
                    if line not in original_text: add_lines.append(line)

            # tier tags
            if f"[[Category:{TAG_TIER2}]]" not in original_text and f"[[Category:{TAG_TIER1}]]" not in original_text:
                add_lines.append(f"[[Category:{TAG_TIER2}]]")

            append_lines_to_page(cat_page, original_text, add_lines)

            # redirects from other sitelinks
            for lang, title in sitelinks.items():
                title = urllib.parse.unquote(title).replace('_',' ')
                if title == tgt: continue
                rpage = local.pages[f"Category:{title}"]
                if not rpage.exists:
                    body = f"#REDIRECT [[Category:{tgt}]]\n[[Category:{TAG_REDIRECT}]]\n"
                    append_lines_to_page(rpage, "", [body])

        time.sleep(THROTTLE)

    print("Finished Tier-2 sync")

if __name__ == '__main__':
    main()