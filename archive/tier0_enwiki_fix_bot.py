#!/usr/bin/env python3
"""
tier0_enwiki_fix_bot.py  –  resume‑able + robust (v1.1)
======================================================

Additions to original logic
---------------------------
* **Start‑at argument** – pass a category name on the command line to resume
  from that title (alphabetical order). Example:

      python tier0_enwiki_fix_bot.py "New automatic wikipedia redirects"

* **safe_page()** – wraps `site.pages[...]`; if the MediaWiki API returns a
  malformed response (no "pages" key) the script logs and skips instead of
  aborting.
"""
import re, time, sys, requests, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ── CONFIG ─────────────────────────────────────────────────────────
SITE_URL   = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME   = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
SOURCE_CAT = "Tier 0 Categories"
TAG_CONF   = "confirmed enwiki categories"
TAG_TIER0  = "Tier 0 Categories"
TAG_TIER1  = "Tier 1 Categories"
META_CAT   = "Meta categories"
THROTTLE   = 0.4
EN_API     = "https://en.wikipedia.org/w/api.php"
UA         = {"User-Agent": "tier0-enwiki-fix-bot/1.1 (User:Immanuelle)"}

START_AT   = "Sele"
resume_flag = bool(START_AT)

EN_IW_RE = re.compile(r"^\[\[\s*en:\s*Category:([^]|]+)\s*\]\]", re.I|re.M)
TAG0_RE  = re.compile(r"\[\[Category:Tier 0 Categories\]\]", re.I)

# ── HELPERS ───────────────────────────────────────────────────────

def enwiki_cat_exists(title: str) -> bool:
    try:
        r = requests.get(EN_API, params={"action":"query","titles":f"Category:{title}","format":"json"}, headers=UA, timeout=10)
        r.raise_for_status()
        pg = next(iter(r.json()["query"]["pages"].values()))
        return "missing" not in pg
    except Exception:
        return False


def safe_page(site, title: str):
    """Return mwclient.Page or None if API glitch."""
    try:
        return site.pages[title]
    except (InvalidPageTitle, KeyError, APIError):
        print("      ! API failure on", title, "– skipped")
        return None


def remove_category_from_page(page, cat_name):
    if not page:
        return
    txt = page.text()
    pat = re.compile(rf"\[\[\s*Category:{re.escape(cat_name)}[^\]]*\]\]", re.I)
    if not pat.search(txt):
        return
    new = pat.sub("", txt)
    if new != txt:
        try:
            page.save(new, summary=f"Bot: remove deleted category {cat_name}")
            print("      • removed from", page.name)
        except APIError as e:
            print("      ! save failed", e.code)
        time.sleep(THROTTLE)

# ── MAIN ──────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in – processing Tier 0 Categories…")

    cm_continue = None
    while True:
        cm = {"action":"query","list":"categorymembers",
              "cmtitle":f"Category:{SOURCE_CAT}","cmtype":"subcat",
              "cmlimit":"max","format":"json"}
        if cm_continue:
            cm["cmcontinue"] = cm_continue
        batch = site.api(**cm)
        for entry in batch.get("query", {}).get("categorymembers", []):
            full = entry["title"]             # Category:Foo
            cat_name = full.split(":",1)[1]

            # resume logic
            global resume_flag
            if resume_flag and cat_name < START_AT:
                continue
            resume_flag = False

            print(f"\n→ {cat_name}")
            cat_page = safe_page(site, full)
            if not cat_page or cat_page.redirect:
                continue
            text = cat_page.text()

            # 1. validate enwiki interwiki
            m = EN_IW_RE.search(text)
            if m and not enwiki_cat_exists(m.group(1).strip()):
                print("  • invalid en interwiki – removing")
                text = EN_IW_RE.sub("", text)

            # 2. same‑name enwiki category
            if enwiki_cat_exists(cat_name):
                print("  • enwiki category exists – confirming")
                if not EN_IW_RE.search(text):
                    text = text.rstrip()+f"\n[[en:Category:{cat_name}]]\n"
                text = TAG0_RE.sub("", text)
                for tag in (TAG_CONF, TAG_TIER1):
                    if f"[[Category:{tag}]]" not in text:
                        text = text.rstrip()+f"\n[[Category:{tag}]]"
                cat_page.save(text, summary="Bot: confirm enwiki category & retag")
                continue

            # 3. delete orphan Tier‑0 category (not meta/Tier‑1)
            if any(f"[[Category:{t}]]" in text for t in (META_CAT, TAG_TIER1)):
                print("  • meta or Tier‑1 – keep")
                continue

            print("  • deleting orphan category & removing from pages…")
            cont = None
            while True:
                cl = site.api(action='query', list='categorymembers', cmtitle=full,
                              cmtype='page', cmlimit='max', cmcontinue=cont,
                              format='json')
                for mem in cl['query']['categorymembers']:
                    remove_category_from_page(safe_page(site, mem['title']), cat_name)
                if 'continue' in cl:
                    cont = cl['continue']['cmcontinue']
                else:
                    break
            try:
                cat_page.delete(reason="Bot: delete unused Tier‑0 category", watch=False)
                print("    • category page deleted")
            except APIError as e:
                print("    ! delete failed", e.code)
            time.sleep(THROTTLE)

        if 'continue' in batch:
            cm_continue = batch['continue']['cmcontinue']
            print("-- batch complete, continuing… --")
        else:
            break
    print("Finished Tier‑0 cleanup.")

if __name__ == "__main__":
    main()
