#!/usr/bin/env python3
"""
tier3_redirect_and_enwiki_check.py
==================================

Behaviour
---------
* Walk every **subcategory** of **Category:Tier 3 Categories**.
* **If the subcategory page is a redirect**:
    1. Detect its target (Category:Target).
    2. On the redirect page:
         • remove `[[Category:Tier 3 Categories]]`
         • add    `[[Category:Tier 3 Categories redirects]]` (if absent)
    3. For every member (pages / subcats / files) of the redirect category:
         • replace `[[Category:Old]]` → `[[Category:Target]]` in the page text.
* **Otherwise (normal category)**:
    • If the page does **not** contain either
        `[Category:Categories created from enwiki title]` **or**
        `[Category:Tier 3 Categories created from enwiki title]`,
      ensure it belongs to `[[Category:Tier 3 Categories with no enwiki]]`.

All edits are throttled; crashes on invalid titles are avoided.
"""
import re, time, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE  = 0.4

SRC_CAT   = "Tier 3 Categories"
REDIRECTS = "Tier 3 Categories redirects"
NO_ENWIKI = "Tier 3 Categories with no enwiki"
ENWIKI_TAGS = {"Categories created from enwiki title",
               "Tier 3 Categories created from enwiki title", "Tier 3 Categories with enwiki"}

REDIR_RX  = re.compile(r"#redirect\s*\[\[\s*Category:([^\]]+)", re.I)

# ─── HELPERS ─────────────────────────────────────────────────────────

def safe_page(site, title):
    try:
        return site.pages[title]
    except (InvalidPageTitle, APIError):
        print("    ! invalid title", title)
        return None


def member_titles(site, cat_full):
    cont = None
    while True:
        cm = site.api(action='query', list='categorymembers', cmtitle=cat_full,
                       cmtype='page|subcat|file', cmlimit='max', cmcontinue=cont,
                       format='json')
        for m in cm['query']['categorymembers']:
            yield m['title']
        if 'continue' in cm:
            cont = cm['continue']['cmcontinue']
        else:
            break


def swap_cat_in_page(page, old, new):
    if not page:
        return
    txt = page.text()
    pat = re.compile(rf"\[\[\s*Category:{re.escape(old)}([^\]]*)\]\]", re.I)
    if not pat.search(txt):
        return
    new_txt = pat.sub(lambda m: f"[[Category:{new}{m.group(1)}]]", txt)
    if new_txt == txt:
        return
    try:
        page.save(new_txt, summary=f"Bot: move category {old} → {new}")
        print("        •", page.name)
    except APIError as e:
        print("        !", page.name, e.code)
    time.sleep(THROTTLE)

# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    print("Logged in – scanning Tier‑3 categories…")

    # fetch Tier‑3 subcategories
    cats = site.api(action='query', list='categorymembers',
                    cmtitle=f"Category:{SRC_CAT}", cmtype='subcat',
                    cmlimit='max', format='json')['query']['categorymembers']

    for ent in cats:
        full  = ent['title']           # Category:Foo
        cname = full.split(':',1)[1]
        print("→", cname)
        catpg = safe_page(site, full)
        if not catpg:
            continue
        txt = catpg.text()

        # ----- handle redirect categories -------------------------
        if catpg.redirect:
            m = REDIR_RX.match(txt)
            if not m:
                print("   ! redirect but target not parsed – skipped")
                continue
            target = m.group(1).strip()
            print("   • redirect →", target)
            # retag the redirect category page
            new_txt = re.sub(rf"\[\[Category:{re.escape(SRC_CAT)}\]\]", "", txt, flags=re.I)
            if f"[[Category:{REDIRECTS}]]" not in new_txt:
                new_txt = new_txt.rstrip()+f"\n[[Category:{REDIRECTS}]]\n"
            if new_txt != txt:
                saveok = False
                try:
                    catpg.save(new_txt, summary="Bot: mark Tier‑3 redirect category")
                    saveok = True
                except APIError as e:
                    print("   ! save failed", e.code)
                if saveok:
                    txt = new_txt
            # move members
            for mt in member_titles(site, full):
                swap_cat_in_page(safe_page(site, mt), cname, target)
            continue

        # ----- normal category – check enwiki creation tags -------
        if any(f"[[Category:{t}]]" in txt for t in ENWIKI_TAGS):
            continue  # already confirmed/created from enwiki
        if f"[[Category:{NO_ENWIKI}]]" not in txt:
            try:
                catpg.save(txt.rstrip()+f"\n[[Category:{NO_ENWIKI}]]\n",
                           summary="Bot: tag Tier‑3 cat with no enwiki")
                print("   • tagged as no‑enwiki")
            except APIError as e:
                print("   ! save failed", e.code)
        time.sleep(THROTTLE)

    print("Finished Tier‑3 sweep.")

if __name__ == "__main__":
    main()
