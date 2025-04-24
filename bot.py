"""orphan_cleanup_and_reformat_bot.py
================================================
A single‑pass maintenance bot for shinto.miraheze.org.
-----------------------------------------------------
Phase 1 – page list (pages.txt)
   • If a title is a **redirect** and **orphaned**, delete it.
   • Otherwise perform one‑shot fixes:
        – Handle {{ill|…}} (create redirects + draft redirects; add |12=draft)
        – Create redirects for missing plain links
        – Reformat main‑namespace pages (move cats/iws/DEFAULTSORT)
        – Remove unwanted categories: qq, Qq, 11, New
        – Ensure every [[Category:Foo]] linked has a redirect target (unless bad)

Phase 2 – Category namespace sweep
   • Strip all ‘#’ characters
   • Remove unwanted categories (qq, Qq, 11, New)
   • Append/replace size tag  [[Category:Categories with N members]]

Put your credentials below and create *pages.txt* alongside the script.
"""

import os
import time
import re
import mwclient

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'
PAGES_TXT = 'pages.txt'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username in a way that works on all mwclient versions
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")

# ─── CONSTANTS & REGEX ──────────────────────────────────────
REMOVE_CATS = {'qq', 'Qq', '11', 'New'}  # exact (case‑sensitive) names
META_TAG_RE = re.compile(r'\[\[Category:Categories with \d+ members\]\]')
CAT_LINK_RE = re.compile(r'\[\[Category:([^\]]+)\]\]')
IWL_RE      = re.compile(r'\[\[[a-z]{2}:[^\]]+\]\]')   # keep 2‑letter codes only
DEF_RE      = re.compile(r'{{\s*DEFAULTSORT\s*:[^}]+}}', re.IGNORECASE)
ILL_RE      = re.compile(r'{{\s*ill\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^}]+?)\s*}}')

BAD_TITLE_CHARS = set('[]{}<>#|')

# ─── GENERIC HELPERS ───────────────────────────────────────

def dedupe(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def safe_save(page, text, summary):
    try:
        page.save(text, summary=summary)
        return True
    except Exception as e:
        print(f"   ! Save failed on [[{page.name}]] – {e}")
        return False


def has_backlinks(page):
    try:
        for _ in page.backlinks(limit=1):
            return True
    except Exception:
        pass
    return False

# ─── REDIRECT CLEANUP ──────────────────────────────────────

def delete_orphan_redirect(page) -> bool:
    if not page.redirect:
        return False
    if has_backlinks(page):
        print(f"   ↳ [[{page.name}]] has backlinks – kept")
        return False
    try:
        page.delete(reason='Bot: orphan redirect', watch=False)
        print(f"   • deleted orphan redirect [[{page.name}]]")
        return True
    except Exception as e:
        print(f"   ! cannot delete [[{page.name}]] – {e}")
        return False

# ─── MAINSPACE REFORMAT ─────────────────────────────────────

def reformat_text(text):
    if text.lstrip().lower().startswith('#redirect'):
        return text

    cats = CAT_LINK_RE.findall(text)
    text = CAT_LINK_RE.sub('', text)

    iws  = IWL_RE.findall(text)
    text = IWL_RE.sub('', text)

    dss  = DEF_RE.findall(text)
    text = DEF_RE.sub('', text)

    cats = dedupe(cats)
    iws  = dedupe(iws)
    dss  = dedupe(dss)

    out = text.rstrip() + '\n\n'
    if cats:
        out += '{{draft categories|\n' + '\n'.join(f'[[Category:{c}]]' for c in cats) + '\n}}\n\n'
    if iws:
        out += '\n'.join(iws) + '\n\n'
    if dss:
        out += '\n'.join(dss) + '\n'
    return out

# ─── ILL TEMPLATE HANDLER ───────────────────────────────────

def handle_ill_templates(text, page_name):
    def repl(match):
        tgt, lang, disp = [x.strip() for x in match.groups()]
        if not tgt or ':' in tgt or '/' in tgt or any(c in tgt for c in BAD_TITLE_CHARS):
            return match.group(0)
        try:
            tgt_page = site.pages[tgt]
        except Exception:
            return match.group(0)

        if not tgt_page.exists:
            redirect = (
                f"#redirect[[:en:{tgt}]]\n"
                "[[Category:automatic wikipedia redirects]]\n"
                "[[Category:pages created from Interlanguage links]]\n"
                f"[[{lang}:{disp}]]"
            )
            safe_save(tgt_page, redirect, f"Bot: ill redirect for [[{page_name}]]")

        draft_page = site.pages[f'draft:{tgt}']
        safe_save(draft_page,
                  f"#redirect[[{tgt}]]\n[[Category:generated draft redirect pages]]",
                  f"Bot: draft ill redirect for [[{page_name}]]")
        return f"{{{{ill|{tgt}|{lang}|{disp}|12=draft}}}}"

    return ILL_RE.sub(repl, text)

# ─── PLAIN LINK REDIRECTS ───────────────────────────────────

def create_redirects_for_plain_links(page):
    links = set(re.findall(r'\[\[([^:\|\]]+)(?:\|[^\]]+)?\]\]', page.text()))
    for raw in links:
        tgt = raw.split('|', 1)[0].strip()
        if not tgt or any(c in tgt for c in BAD_TITLE_CHARS):
            continue
        tgt_page = site.pages[tgt]
        if not tgt_page.exists:
            txt = f"#redirect[[:en:{tgt}]]\n[[Category:automatic wikipedia redirects]]"
            safe_save(tgt_page, txt, f"Bot: plain‑link redirect from [[{page.name}]]")

# ─── CATEGORY REDIRECT ENSURER ───────────────────────────────

def ensure_category_redirect(page):
    for raw in CAT_LINK_RE.findall(page.text()):
        name = raw.split('|', 1)[0].strip()
        if not name or name in REMOVE_CATS or any(c in name for c in BAD_TITLE_CHARS):
            continue
        title = f'Category:{name}'
        try:
            cat_page = site.pages[title]
        except Exception:
            continue
        if not cat_page.exists:
            txt = (
                f"#redirect[[:en:{title}]]\n"
                "[[Category:Bot created categories]]"
            )
            if safe_save(cat_page, txt, f"Bot: create cat redirect from [[{page.name}]]"):
                print(f"   • cat redirect [[{title}]] created")

# ─── PER‑PAGE DRIVER ─────────────────────────────────────────

def process_page(page):
    if delete_orphan_redirect(page):
        return  # page deleted

    original = page.text()
    new      = handle_ill_templates(original, page.name)
    create_redirects_for_plain_links(page)

    if page.namespace == 0:
        new = reformat_text(new)
        ensure_category_redirect(page)

    # remove unwanted category links everywhere
    for bad in REMOVE_CATS:
        new = re.sub(rf"\[\[Category:{re.escape(bad)}\]\]", '', new, flags=re.IGNORECASE)

    if new.strip() != original.strip():
        if safe_save(page, new, "Bot: cleanup/reformat"):
            print(f"   • saved [[{page.name}]]")

# ─── CATEGORY TIDIER ─────────────────────────────────────────

def tidy_category(cat_page):
    """Strip '#', remove unwanted cat links, add a size-tag reflecting
    the current number of pages in the category (ignoring sub-cats/files)."""
    original = cat_page.text()

    # 1) remove all literal '#'
    cleaned = original.replace('#', '')

    # 2) drop unwanted categories and any old size tag
    for bad in REMOVE_CATS:
        cleaned = re.sub(rf"\[\[Category:{re.escape(bad)}\]\]", '', cleaned, flags=re.IGNORECASE)
    cleaned = META_TAG_RE.sub('', cleaned).rstrip()

    # 3) fetch live page-count via API
    members = 0
    try:
        data = site.api('query', prop='categoryinfo', titles=cat_page.name)
        page_info = next(iter(data['query']['pages'].values()))
        members = page_info.get('categoryinfo', {}).get('pages', 0)
    except Exception as e:
        print(f"   ! size fetch failed on [[{cat_page.name}]] – {e}")

    # 4) append size tag with proper newlines
    size_tag = f"[[Category:Categories with {members} members]]"
    if size_tag not in cleaned:
        cleaned += "\n" + size_tag + "\n"

    # 5) save if anything changed
    if cleaned != original:
        if safe_save(cat_page, cleaned, f"Bot: tidy & size tag ({members} members)"):
            print(f"   • tidied [[{cat_page.name}]] ({members} members)")

# ─── MAIN ───────────────────────────────────────────────────

def main():
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT, 'w', encoding='utf-8').close()
        print(f"Created empty {PAGES_TXT}; add titles and re‑run.")
        return

    with open(PAGES_TXT, 'r', encoding='utf-8', errors='ignore') as fh:
        titles = [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]

    # Phase 1 – process explicit list
    print("—— Page processing (list) ——————————————————————————")
    for idx, title in enumerate(titles, 1):
        print(f"{idx}/{len(titles)} [[{title}]]")
        page = site.pages[title]
        process_page(page)
        time.sleep(1)

    # Phase 2 – category maintenance
    print("—— Category maintenance ——————————————————————————")
    for idx, cat in enumerate(site.allpages(namespace=14), 1):
        tidy_category(cat)
        time.sleep(1)

    print("Done!")


if __name__ == '__main__':
    main()
