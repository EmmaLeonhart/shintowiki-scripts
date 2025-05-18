#!/usr/bin/env python3
"""
category_interwiki_restore_bot.py  –  Tier 2 Category Sync (Multi‑lang)
=====================================================================

For each Tier 1 category in pages.txt, create or confirm a Tier 2 category
on the local wiki based on its interwiki categories (English, Commons,
Japanese, German) in that priority. All other interwiki names redirect to
the chosen local category. Pages are never overwritten—new content is
appended.

Behavior per source category (Tier 1):
1. Fetch its Wikidata QID via local pageprops.
2. Pull sitelinks: enwiki, commonswiki, jawiki, dewiki.
3. Choose primary lang in order: enwiki → commonswiki → jawiki → dewiki.
4. Let `chosen` = the interwiki title for that lang. `via` = that code.
5. Ensure local Category:<chosen> exists:
   - If exists and *redirect*, follow to target.
   - If not exists, create a new page and append `[[Category:Categories created from <via> title]]`.
   - If exists non-redirect, append `[[Category:Categories confirmed during Tier 2 run]]` (if missing).
6. Append all available interwiki links on the category page with comment headers.
7. Create redirects for every other interwiki code→local Category:<chosen> (tag with `[[Category:Tier 2 redirect categories]]`).
8. Append `[[Category:Tier 2 Categories]]` if absent.
9. Throttle edits between actions.

Edit summary: "Bot: sync Tier 2 category from interwiki"
"""
import os, re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL    = "shinto.miraheze.org"
SITE_PATH   = "/w/"
USERNAME    = "Immanuelle"
PASSWORD    = "[REDACTED_SECRET_1]"
PAGES_FILE  = "pages.txt"
THROTTLE    = 0.5
WD_API      = "https://www.wikidata.org/w/api.php"

# Tags
TAG_CONFIRMED    = "Categories confirmed during Tier 2 run"
TAG_EN_NEW       = "Categories created from enwiki title"
TAG_COMMONS_NEW  = "Categories created from commonswiki title"
TAG_JA_NEW       = "Categories created from jawiki title"
TAG_DE_NEW       = "Categories created from dewiki title"
TAG_REDIRECT     = "Tier 2 redirect categories"
TAG_TIER2        = "Tier 2 Categories"

ORDER = [
    ("enwiki",    "en",      TAG_EN_NEW),
    ("commonswiki","commons",TAG_COMMONS_NEW),
    ("jawiki",    "ja",      TAG_JA_NEW),
    ("dewiki",    "de",      TAG_DE_NEW),
]
USER_AGENT = {"User-Agent": "tier2-cat-bot/1.0 (User:Immanuelle)"}

# ─── HELPERS ────────────────────────────────────────────────────────

def load_titles(path):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def get_qid(site, cat):
    rv = site.api(
        action="query",
        titles=f"Category:{cat}",
        prop="pageprops",
        ppprop="wikibase_item"
    )
    pages = rv.get("query", {}).get("pages", {})
    for p in pages.values():
        return p.get("pageprops", {}).get("wikibase_item")
    return None


def get_sitelinks(qid):
    params = {"action":"wbgetentities","ids":qid,
              "props":"sitelinks","format":"json"}
    r = requests.get(WD_API, params=params, headers=USER_AGENT, timeout=15)
    r.raise_for_status()
    ent = r.json().get("entities", {}).get(qid, {})
    sl = ent.get("sitelinks", {})
    return {k: v.get("title") for k,v in sl.items()}


def existing_redirect_target(site, name):
    pg = site.pages[f"Category:{name}"]
    if not pg.exists:
        return None
    try:
        txt = pg.text().strip()
    except:
        return None
    m = re.match(r"#redirect\s*\[\[Category:([^\]]+)\]\]", txt, re.I)
    return m.group(1) if m else None


def save_page(page, body, summary):
    try:
        page.save(body, summary=summary)
    except APIError as e:
        print(f"  ! save failed: {e.code}")

# ─── CORE ────────────────────────────────────────────────────────────

def process_cat(site, cat):
    print(f"Processing Tier1 category → {cat}")
    qid = get_qid(site, cat)
    if not qid:
        print("  ! no QID; skipped")
        return
    sl = get_sitelinks(qid)
    # pick primary
    chosen_name = None
    via_tag     = None
    for code, lang, tag_new in ORDER:
        key = code
        if key in sl:
            chosen_name = sl[key]
            via_tag = tag_new
            break
    if not chosen_name:
        print("  ! no interwiki; skipped")
        return
    # normalize
    chosen_name = urllib.parse.unquote(chosen_name).replace('_',' ')
    # resolve existing redirect
    redir = existing_redirect_target(site, chosen_name)
    if redir:
        chosen_name = redir
    full = f"Category:{chosen_name}"
    page = site.pages[full]
    exists = page.exists and not page.redirect

    text = page.text() if exists else ""
    new_lines = []

    # creation or confirmation tag
    if exists:
        tag = TAG_CONFIRMED
    else:
        tag = via_tag
    line_tag = f"[[Category:{tag}]]"
    if line_tag not in text:
        new_lines.append(line_tag)

    # append all interwikis found
    for code, lang, _ in ORDER:
        key = code
        if key in sl:
            name = urllib.parse.unquote(sl[key]).replace('_',' ')
            if code == 'enwiki':
                l = f"<!--enwiki derived category-->\n[[en:Category:{name}]]"
            elif code == 'commonswiki':
                l = f"<!--commons derived category-->\n{{{{Commons category|{name}}}}}"
            elif code == 'jawiki':
                l = f"<!--jawiki derived category-->\n[[ja:Category:{name}]]"
            else:
                l = f"<!--dewiki derived category-->\n[[de:Category:{name}]]"
            if l not in text:
                new_lines.append(l)

    # Tier 2 tag
    tier2_line = f"[[Category:{TAG_TIER2}]]"
    if tier2_line not in text:
        new_lines.append(tier2_line)

    # save or create page
    if new_lines:
        body = (text.rstrip() + "\n" + "\n".join(new_lines) + "\n") if exists else (
            # new page header
            "" + "\n".join(new_lines) + "\n"
        )
        save_page(page, body, "Bot: sync Tier 2 category from interwiki")
        print(f"  ✓ updated/created {full}")
    else:
        print("  • nothing new; skipped")

    # redirect others
    for code, lang, _ in ORDER:
        key = code
        if key in sl and sl[key] != chosen_name:
            other = urllib.parse.unquote(sl[key]).replace('_',' ')
            red_pg = site.pages[f"Category:{other}"]
            if not red_pg.exists:
                body = f"#redirect [[Category:{chosen_name}]]\n[[Category:{TAG_REDIRECT}]]\n"
                save_page(red_pg, body, "Bot: Tier2 redirect setup")
                print(f"  ↳ redirect created from {other}")

    time.sleep(THROTTLE)

# ─── MAIN LOOP ──────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)
    titles = load_titles(PAGES_FILE)
    for cat in titles:
        process_cat(site, cat)
    print("Done Tier 2 sync.")

if __name__ == '__main__':
    main()
