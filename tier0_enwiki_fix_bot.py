#!/usr/bin/env python3
"""
tier0_enwiki_fix_bot.py
=======================

Cleans up categories that currently belong to **[[Category:Tier 0 Categories]]**.

Rules for each Tier-0 category C:
1. **Validate existing enwiki interwiki**
   * If C’s wikitext contains an `[[en:Category:X]]` interwiki and the
     category *X* does **not** exist on English Wikipedia → **remove** the
     interwiki line.
2. **Check for same-name enwiki category**
   * Query enwiki for *Category:C* (exact title).
   * If it exists:
       • Ensure `[[en:Category:C]]` interwiki line is present.
       • Remove `[[Category:Tier 0 Categories]]`.
       • Add  `[[Category:confirmed enwiki categories]]` and
         `[[Category:Tier 1 Categories]]`.
3. **Otherwise delete empty Tier-0 category**
   * If no enwiki category exists for C **and** C is *not* already in
     `[[Category:Meta categories]]` nor `[[Category:Tier 1 Categories]]`,
     then:
       • Remove C from every page that transcludes it.
       • Delete the category page itself.

The script handles large categorymember lists using `cmcontinue`.
"""

import os, re, time, requests, mwclient
from mwclient.errors import APIError

# ── CONFIG ─────────────────────────────────────────────────────────
SITE_URL   = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME   = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
SOURCE_CAT = "Tier 0 Categories"
TAG_CONF   = "confirmed enwiki categories"
TAG_TIER0  = "Tier 0 Categories"
TAG_TIER1  = "Tier 1 Categories"
META_CAT   = "Meta categories"
THROTTLE   = 0.5
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "tier0-enwiki-fix-bot/1.0 (User:Immanuelle)"}

EN_IW_RE   = re.compile(r"^\[\[\s*en:\s*Category:([^]|]+)\s*\]\]", re.I|re.M)
TAG0_RE    = re.compile(r"\[\[Category:Tier 0 Categories\]\]", re.I)

# ── HELPERS ───────────────────────────────────────────────────────

def enwiki_cat_exists(title: str) -> bool:
    params = {"action":"query","titles":f"Category:{title}","format":"json"}
    try:
        r = requests.get(EN_API, params=params, headers=UA, timeout=10)
        r.raise_for_status()
        pg = next(iter(r.json()["query"]["pages"].values()))
        return "missing" not in pg
    except Exception:
        return False


def remove_category_from_page(page: mwclient.page, cat_name: str):
    txt = page.text()
    pattern = re.compile(rf"\[\[\s*Category:{re.escape(cat_name)}[^\]]*\]\]", re.I)
    if not pattern.search(txt):
        return
    new = pattern.sub("", txt)
    if new != txt:
        try:
            page.save(new, summary=f"Bot: remove deleted category {cat_name}")
            print(f"      • removed from {page.name}")
        except APIError as e:
            print(f"      ! failed to update {page.name}: {e.code}")
            time.sleep(THROTTLE)

# ── MAIN ──────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in – processing Tier 0 Categories…")

    cm_continue = None
    while True:
        cm = {
            "action": "query", "list": "categorymembers",
            "cmtitle": f"Category:{SOURCE_CAT}", "cmtype": "subcat",
            "cmlimit": "max", "format": "json"
        }
        if cm_continue:
            cm["cmcontinue"] = cm_continue
        data = site.api(**cm)
        members = data.get("query", {}).get("categorymembers", [])

        for entry in members:
            full = entry["title"]               # Category:Foo
            cat_name = full.split(":",1)[1]
            print(f"\n→ {cat_name}")
            cat_page = site.pages[full]
            if cat_page.redirect:
                print("  • redirect – skipped"); continue
            text = cat_page.text()

            # ------- 1. validate existing enwiki interwiki ----------
            m = EN_IW_RE.search(text)
            if m:
                en_link = m.group(1).strip()
                if not enwiki_cat_exists(en_link):
                    print("  • invalid en interwiki – removing line")
                    text = EN_IW_RE.sub("", text)

            # ------- 2. check same-name enwiki category -------------
            if enwiki_cat_exists(cat_name):
                print("  • enwiki category exists → confirm")
                # ensure interwiki present
                if not EN_IW_RE.search(text):
                    text = text.rstrip() + f"\n[[en:Category:{cat_name}]]\n"
                # swap tags
                if TAG0_RE.search(text):
                    text = TAG0_RE.sub("", text)
                for tag in (TAG_CONF, TAG_TIER1):
                    if f"[[Category:{tag}]]" not in text:
                        text = text.rstrip() + f"\n[[Category:{tag}]]"
                # save changes
                cat_page.save(text, summary="Bot: confirm enwiki category & retag")
                continue  # done with this category

            # ------- 3. delete orphan Tier-0 category ---------------
            if (f"[[Category:{META_CAT}]]" in text or
                f"[[Category:{TAG_TIER1}]]" in text):
                print("  • meta or Tier-1 – keep")
                continue

            print("  • deleting orphan category & removing from pages…")
            # remove category from member pages first
            cl = site.api(action="query", list="categorymembers", cmtitle=full,
                          cmtype="page", cmlimit="max", format="json")
            for mem in cl.get("query", {}).get("categorymembers", []):
                remove_category_from_page(site.pages[mem["title"]], cat_name)
            # delete category page
            try:
                cat_page.delete(reason="Bot: delete unused Tier-0 category", watch=False)
                print("    • category page deleted")
            except APIError as e:
                print("    ! delete failed", e.code)
            time.sleep(THROTTLE)

        if "continue" in data:
            cm_continue = data["continue"].get("cmcontinue")
            print("-- batch complete, continuing… --")
        else:
            break

    print("Finished Tier-0 cleanup.")

if __name__ == "__main__":
    main()
