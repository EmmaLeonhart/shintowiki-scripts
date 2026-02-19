"""
category_cleanup_bot.py
=======================
Scans all categories (ns=14) on Shinto Wiki and:
 1. Skips any category listed in [[Category:Important original categories]].
 2. Removes any self-category link from the category page (a category must not categorize itself).
 3. On a mainspace page whose title matches the category name, removes that category only if it is the sole category on that page (so accidental single-membership pages are cleaned but valid multi-member categories keep their page).
 4. After those edits, if the category has zero pages + zero subcategories:
    • Deletes it when no backlinks.
    • Else replaces it with an English redirect stub to "en:{{subst:PAGENAME}}" tagged [[Category:redirect categories]].

Configure USERNAME/PASSWORD, then run:
    python category_cleanup_bot.py
"""

import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_2]'
THROTTLE   = 1.0  # seconds between edits
IMPORTANT_CAT = 'Important original categories'

# ─── CONNECT ────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in as {site.userinfo.get('name')}")

# ─── HELPERS ───────────────────────────────────────────────────────

def safe_save(page, text, summary):
    try:
        page.save(text, summary=summary)
        return True
    except APIError as e:
        print(f"   ! Save failed [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"   ! Exception saving [[{page.name}]]: {e}")
    return False


def has_backlinks(page):
    try:
        for _ in page.backlinks(limit=1):
            return True
    except Exception:
        pass
    return False


def _cat_member_count(cat_page):
    try:
        data = site.api('query', prop='categoryinfo', titles=cat_page.name)
        info = next(iter(data['query']['pages'].values()))
        ci = info.get('categoryinfo', {})
        return ci.get('pages', 0) + ci.get('subcats', 0)
    except Exception as e:
        print(f"   ! Failed member count [[{cat_page.name}]]: {e}")
        return 0

# regex to find category links
CAT_LINK_RE = re.compile(r"\[\[Category:([^\]|]+)\]\]")

# ─── MAIN LOOP ─────────────────────────────────────────────────────
for idx, cat_page in enumerate(site.allpages(namespace=14, start="eo"), start=1):
    cat_title = cat_page.name            # e.g. 'Category:Foo'
    cat_name  = cat_title.split(':',1)[1]
    print(f"{idx}. [[{cat_title}]]")

    text = cat_page.text()
    # 1) skip important
    if f'[[Category:{IMPORTANT_CAT}]]' in text:
        print(f"   ↳ Skipped (in {IMPORTANT_CAT})")
        continue

    # 2) remove any self-category link
    self_link = f'[[Category:{cat_name}]]'
    if self_link in text:
        new_text = text.replace(self_link, '')
        if safe_save(cat_page, new_text, 'Bot: remove self-category link'):
            print(f"   • Removed self-category link")
            time.sleep(THROTTLE)
        text = new_text

    # 3) remove this category from mainspace page of same name if sole
    member_page = site.pages[cat_name]
    if member_page.exists:
        m_text = member_page.text()
        m_cats = CAT_LINK_RE.findall(m_text)
        if m_cats == [cat_name]:
            m_new = m_text.replace(f'[[Category:{cat_name}]]', '')
            if safe_save(member_page, m_new, f"Bot: remove [[Category:{cat_name}]] from itself"):
                print(f"   • Removed category from [[{cat_name}]]")
                time.sleep(THROTTLE)

    # 4) handle empty category
    members = _cat_member_count(cat_page)
    if members == 0:
        if not has_backlinks(cat_page):
            try:
                cat_page.delete(reason='Bot: delete empty orphan category', watch=False)
                print(f"   • Deleted empty orphan category")
            except APIError as e:
                print(f"   ! Delete failed: {e.code}")
        else:
            stub = (
                f"#redirect [[en:{{subst:PAGENAME}}]]\n"
                "[[Category:redirect categories]]"
            )
            if safe_save(cat_page, stub, 'Bot: redirect empty category'):
                print(f"   • Redirected empty category")
        time.sleep(THROTTLE)

print("Done processing categories.")
