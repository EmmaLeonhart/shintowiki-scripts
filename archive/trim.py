"""
orphan_cleanup_and_reformat_bot.py
================================================
A single-pass maintenance bot for shinto.miraheze.org.

Phase 1 – specified pages (pages.txt):
  • Delete orphan redirects (including malformed #redirect[[...]]).
  • Tidy remaining redirects (strip cats, add letter-bucket auto-cat).
  • Handle {{ill}} templates (normal + draft redirects; append |12=draft).
  • Create redirects for missing plain [[links]].
  • Reformat mainspace pages (move cats, interwikis, DEFAULTSORT).
  • Remove unwanted categories (qq, Qq, 11, New).
  • Ensure category redirect pages exist.

Phase 2 – Category namespace sweep:
  • Strip all '#' characters.
  • Remove unwanted categories.
  • Append/update size tag [[Category:Categories with N members]].

Usage:
  - Populate pages.txt (one title per line) alongside this script.
  - Run: python orphan_cleanup_and_reformat_bot.py
"""
import os
import time
import re
import mwclient

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
PAGES_FILE = 'pages.txt'

REMOVE_CATS = {'qq', 'Qq', '11', 'New'}
META_TAG_RE = re.compile(r"\[\[Category:Categories with \d+ members\]\]")
CAT_LINK_RE = re.compile(r"\[\[Category:([^\]]+)\]\]")
IWL_RE      = re.compile(r"\[\[[a-z]{2}:[^\]]+\]\]")
DEF_RE      = re.compile(r"{{\s*DEFAULTSORT\s*:[^}]+}}", re.IGNORECASE)
ILL_RE      = re.compile(r"{{\s*ill\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^}]+?)\s*}}")
BAD_CHARS   = set('[]{}<>#|')

# ─── CONNECT ──────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# ─── HELPERS ──────────────────────────────────────────────────
def dedupe(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


def safe_save(page, text, summary):
    if not page.exists:
        return False
    try:
        current = page.text()
    except Exception:
        current = None
    if current is not None and current.rstrip() == text.rstrip():
        return False
    try:
        page.save(text, summary=summary)
        return True
    except Exception as e:
        print(f"   ! Save failed [[{page.name}]] – {e}")
        return False


def has_backlinks(page):
    try:
        for _ in page.backlinks(limit=1):
            return True
    except Exception:
        pass
    return False

# ─── ORPHAN REDIRECT CLEANUP ──────────────────────────────────

def delete_orphan_redirect(page) -> bool:
    try:
        txt = page.text()
    except Exception:
        return False
    # detect redirect via flag or raw text
    is_redirect = page.redirect or txt.lstrip().lower().startswith('#redirect')
    if not is_redirect:
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

# ─── REDIRECT TIDIER ─────────────────────────────────────────

def tidy_redirect(page) -> bool:
    if not page.redirect and not page.text().lstrip().lower().startswith('#redirect'):
        return False
    original = page.text()
    # remove all category links
    cleaned = CAT_LINK_RE.sub('', original)
    cleaned = re.sub(
    r'\[\[Category:automatic wikipedia redirects[^\]]*\]\]',
    '',
    cleaned,
    flags=re.IGNORECASE
)

    cleaned = cleaned.rstrip()
    if cleaned.lstrip().lower().startswith('#redirect'):
        bucket = page.name[0].upper()
        cleaned += f"\n[[Category:automatic wikipedia redirects {bucket}]]\n"
    else:
        cleaned += "\n"
    if cleaned != original:
        if safe_save(page, cleaned, 'Bot: tidy redirect'): 
            print(f"   • tidied redirect [[{page.name}]]")
            return True
    return False

# ─── MAINSPACE REFORMAT ──────────────────────────────────────

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


def handle_ill_templates(text, page_name):
    def repl(m):
        tgt, lang, disp = [x.strip() for x in m.groups()]
        if not tgt or any(c in tgt for c in BAD_CHARS) or ':' in tgt or '/' in tgt:
            return m.group(0)
        tgt_page = site.pages[tgt]
        if not tgt_page.exists:
            redirect = (f"#redirect[[:en:{tgt}]]\n"
                        "[[Category:automatic wikipedia redirects]]\n"
                        "[[Category:pages created from Interlanguage links]]\n"
                        f"[[{lang}:{disp}]]")
            safe_save(tgt_page, redirect, f"Bot: ill redirect for [[{page_name}]]")
        draft = site.pages[f'draft:{tgt}']
        safe_save(draft, f"#redirect[[{tgt}]]\n[[Category:generated draft redirect pages]]",
                  f"Bot: draft ill redirect for [[{page_name}]]")
        return f"{{{{ill|{tgt}|{lang}|{disp}|12=draft}}}}"
    return ILL_RE.sub(repl, text)


def create_redirects_for_plain_links(page):
    links = set(re.findall(r"\[\[([^:\|\]]+)(?:\|[^\]]+)?\]\]", page.text()))
    for raw in links:
        tgt = raw.split('|',1)[0].strip()
        if not tgt or any(c in tgt for c in BAD_CHARS):
            continue
        tgt_page = site.pages[tgt]
        if not tgt_page.exists:
            txt = f"#redirect[[:en:{tgt}]]\n[[Category:automatic wikipedia redirects]]"
            safe_save(tgt_page, txt, f"Bot: link redirect from [[{page.name}]]")


def ensure_category_redirect(page):
    for raw in CAT_LINK_RE.findall(page.text()):
        name = raw.split('|',1)[0].strip()
        if not name or name in REMOVE_CATS or any(c in name for c in BAD_CHARS):
            continue
        title = f'Category:{name}'
        cat_page = site.pages[title]
        if not cat_page.exists:
            txt = f"#redirect[[:en:{title}]]\n[[Category:Bot created categories]]"
            if safe_save(cat_page, txt, f"Bot: cat redirect from [[{page.name}]]"):
                print(f"   • cat redirect [[{title}]] created")

# ─── CATEGORY TIDIER ──────────────────────────────────────────
def _cat_member_count(cat_page) -> int:
    try:
        data = site.api('query', prop='categoryinfo', titles=cat_page.name)
        info = next(iter(data['query']['pages'].values()))
        ci = info.get('categoryinfo', {})
        return ci.get('pages',0) + ci.get('subcats',0)
    except:
        return 0


def tidy_category(cat_page):
    count = _cat_member_count(cat_page)
    if count == 0:
        if not has_backlinks(cat_page):
            try:
                cat_page.delete(reason='Bot: empty orphan category', watch=False)
                print(f"   • deleted [[{cat_page.name}]]")
            except Exception as e:
                print(f"   ! delete failed [[{cat_page.name}]] – {e}")
        else:
            stub = ("#redirect[[:en:{{subst:PAGENAME}}]]\n"
                    "[[Category:redirect categories]]\n")
            if safe_save(cat_page, stub, 'Bot: empty category redirect'):
                print(f"   • redirected [[{cat_page.name}]]")
        return
    # non-empty category
    original = cat_page.text()
    cleaned = original.replace('#','')
    for bad in REMOVE_CATS:
        cleaned = re.sub(rf"\[\[Category:{re.escape(bad)}\]\]", '', cleaned, flags=re.IGNORECASE)
    cleaned = META_TAG_RE.sub('', cleaned).rstrip()
    size_tag = f"[[Category:Categories with {count} members]]"
    if size_tag not in cleaned:
        cleaned += '\n' + size_tag + '\n'
    if cleaned != original:
        if safe_save(cat_page, cleaned, f"Bot: tidy category ({count})"): print(f"   • tidied [[{cat_page.name}]]")

# ─── PROCESS A SINGLE PAGE ───────────────────────────────────
def process_page(page):
    if delete_orphan_redirect(page): return
    if tidy_redirect(page):        return
    orig = page.text()
    new  = handle_ill_templates(orig, page.name)
    create_redirects_for_plain_links(page)
    new  = reformat_text(new)
    ensure_category_redirect(page)
    # drop unwanted cats
    new = re.sub(rf"\[\[Category:%s\]\]" % '|'.join(map(re.escape,REMOVE_CATS)), '', new, flags=re.IGNORECASE)
    if new.strip() != orig.strip():
        if safe_save(page, new, 'Bot: reformat'): print(f"   • saved [[{page.name}]]")

# ─── MAIN ─────────────────────────────────────────────────────
def main():
    """Sweep mainspace from pages starting with 'Draft', then Category namespace."""
    # Phase 1: iterate mainspace pages starting at 'Draft'
    print("→ Mainspace sweep starting at 'Draft'...")
    for idx, page in enumerate(site.allpages(namespace=0, start='Draft'), 1):
        print(f"{idx}: [[{page.name}]]")
        process_page(page)
        time.sleep(1)

    # Phase 2: Category maintenance
    print("→ Category maintenance sweep...")
    for idx, cat in enumerate(site.allpages(namespace=14), 1):
        tidy_category(cat)
        time.sleep(1)

if __name__ == '__main__':

    main()
