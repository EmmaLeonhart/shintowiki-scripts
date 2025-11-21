#!/usr/bin/env python3
"""
tier5_redirect_fix_bot.py
=========================
• Scans **Tier 5 Categories with no enwiki** for redirect‑categories.
• Rewrites every member page to use the redirect target.
• **Now also strips *all* category lines from the redirect page itself** once
  its members have been moved.

Hard‑coded credentials at the top – edit if needed.
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import re, sys, urllib.parse, time
from typing import List
import mwclient
from mwclient.errors import APIError

SRC_CAT   = "Category:Tier 5 Categories with no enwiki"
THROTTLE  = 0.4
SUMMARY   = "Bot: replace redirect cat [[{old}]] → [[{new}]]"
CLEAN_SUM = "Bot: clear categories from redirect"

REDIR_RX = re.compile(r"#redirect\s*\[\[\s*:?(?:category)?:?\s*([^]|]+)", re.I)
CAT_LINE_RX = re.compile(r"^\s*\[\[Category:[^]]+]]\s*$", re.I | re.M)

# ─── site login ───────────────────────────────────────────────────

def get_site() -> mwclient.Site:
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php", 1)[0] + "/")
    s.login(USERNAME, PASSWORD)
    return s

# ─── fetch members (pages + subcats) ──────────────────────────────

def fetch_members(site: mwclient.Site, cat: str) -> List[mwclient.page]:
    members, cont = [], None
    while True:
        data = site.api(action='query', list='categorymembers', cmtitle=cat,
                        cmtype='page|subcat', cmlimit='5000',
                        **({"cmcontinue": cont} if cont else {}))
        members.extend(site.pages[m['title']] for m in data['query']['categorymembers'])
        cont = data.get('continue', {}).get('cmcontinue')
        if not cont:
            break
    return members

# ─── regex helpers ────────────────────────────────────────────────

def fuzzy(title: str) -> str:
    parts = [re.escape(p) for p in title.split(' ') if p]
    return r"[ _\s]*".join(parts)


def cat_regex(old: str) -> re.Pattern:
    ns = r"[Cc]ategor(?:y|ie)"  # also matches German "Kategorie"
    return re.compile(fr"\[\[\s*{ns}\s*:\s*{fuzzy(old)}\s*(\|[^]]*)?]]", re.I)


def swap_links(text: str, old: str, new: str):
    return cat_regex(old).sub(lambda m: f"[[Category:{new}{m.group(1) or ''}]]", text)

# ─── main ─────────────────────────────────────────────────────────

def main():
    site = get_site()
    print("Logged in – scanning redirect Tier‑5 cats…")

    cats = site.api(action='query', list='categorymembers', cmtitle=SRC_CAT,
                    cmtype='subcat', cmlimit='max', format='json')['query']['categorymembers']

    for ent in cats:
        full = ent['title']
        cat_name = full.split(':', 1)[1]
        cat_page = site.pages[full]
        txt = cat_page.text()
        m = REDIR_RX.match(txt)
        if not m:
            continue
        target = urllib.parse.unquote(m.group(1)).replace('_', ' ').strip()
        if not target.lower().startswith('category:'):
            target = f"Category:{target}"
        target_name = target.split(':', 1)[1]
        print(f"→ {cat_name} redirects → {target_name}")

        # 1) update all members
        for pg in fetch_members(site, full):
            new_txt = swap_links(pg.text(), cat_name, target_name)
            if new_txt == pg.text():
                continue
            try:
                pg.save(new_txt, summary=SUMMARY.format(old=cat_name, new=target_name))
                print("   •", pg.name)
            except APIError as e:
                print("   ! save failed", pg.name, e.code)
            time.sleep(THROTTLE)

        # 2) strip category lines from the redirect page itself
        cleaned = CAT_LINE_RX.sub("", txt).rstrip() + "\n"
        if cleaned != txt:
            try:
                cat_page.save(cleaned, summary=CLEAN_SUM)
                print("   • cleaned categories on redirect page")
            except APIError as e:
                print("   ! couldn't clean redirect page", e.code)
            time.sleep(THROTTLE)

    print("Done.")


if __name__ == '__main__':
    main()
