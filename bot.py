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
    """Attempt Page.save but gracefully back off on edit‑conflict or if
    the page vanished (was deleted) before we got to save."""
    if not page.exists:
        print(f"   • skipped save, page [[{page.name}]] no longer exists")
        return False

    # Nothing to do if text hasn't changed
    try:
        current = page.text()
    except Exception:
        current = None
    if current is not None and current.rstrip() == text.rstrip():
        return False

    try:
        page.save(text, summary=summary)
        return True
    except mwclient.errors.EditError as e:
        if getattr(e, "code", "") == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
    except mwclient.errors.APIError as e:
        if e.code == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]] – skipping")
            return False
        raise
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


# helper methods

import re

# removes generic or letter‑specific auto‑redirect cats, e.g.
# [[Category:automatic wikipedia redirects]]
# [[Category:automatic wikipedia redirects A]]
_AUTO_RE = re.compile(r"\[\[Category:automatic wikipedia redirects[^\]]*\]\]", re.I)

_EN_REDIRECT_RE = re.compile(r"^\s*(#redirect\s*)?\[\[\s*:?en:[^\]]+\]\]", re.I)

def tidy_redirect(page) -> bool:
    """Strip category links from redirects and add letter‑bucket auto
    category for redirects that target English Wikipedia.

    Returns **True** if the page was modified & saved, else False."""

    # Skip non‑redirects (unless soft en: redirect pattern matches)
    if not page.redirect and not _EN_REDIRECT_RE.match(page.text()):
        return False

    original = page.text()

    # 1 – remove all category links (including old auto‑cats)
    cleaned = CAT_LINK_RE.sub("", original)
    cleaned = _AUTO_RE.sub("", cleaned)
    cleaned = cleaned.rstrip()

    # 2 – if it’s an en: redirect, append the letter bucket cat
    if _EN_REDIRECT_RE.match(cleaned):
        bucket = page.name[0].upper()
        cleaned += f"\n[[Category:automatic wikipedia redirects {bucket}]]\n"
    else:
        cleaned += "\n"  # ensure trailing newline

    # 3 – save when changed
    if cleaned != original:
        if safe_save(page, cleaned, "Bot: tidy redirect categories"):
            print(f"   • tidied redirect [[{page.name}]]")
            return True
    return False

# ─── PER‑PAGE DRIVER ─────────────────────────────────────────

def process_page(page):
    if delete_orphan_redirect(page):
        return  # page deleted
    
        # NEW: tidy redirect pages ------------------------------------
    if tidy_redirect(page):
        return  # redirect cleaned; nothing more to do


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

# Patch: improved tidy_category for orphan_cleanup_and_reformat_bot
# -----------------------------------------------------------------
# Drop this function (and the tiny helper below) into your main script
# to replace the existing tidy_category.  It now handles **all** rules:
#   • If a category has **zero pages + zero subcategories**
#       – delete when it also has no backlinks
#       – otherwise overwrite with a redirect stub to English and
#         tag it with [[Category:redirect categories]]
#   • Otherwise (it has at least one page or subcat) tidy text, strip
#     literal '#', remove unwanted cats/meta‑tag, and append / update
#     the size‑tag  [[Category:Categories with N members]] — where N is
#     **pages + subcats** (files are ignored).
#
# It relies on the same globals/functions already present:  site,
# REMOVE_CATS, META_TAG_RE, safe_save, has_backlinks.
# --------------------------------------------------------------------

import re

# helper --------------------------------------------------------------

def _cat_member_count(cat_page) -> int:
    """Return *pages + subcats* in cat_page using categoryinfo."""
    try:
        data = site.api("query", prop="categoryinfo", titles=cat_page.name)
        page_info = next(iter(data["query"]["pages"].values()))
        ci = page_info.get("categoryinfo", {})
        return ci.get("pages", 0) + ci.get("subcats", 0)
    except Exception as e:
        print(f"   ! size fetch failed on [[{cat_page.name}]] – {e}")
        return 0

# main ----------------------------------------------------------------

def tidy_category(cat_page):
    """Maintain *cat_page* according to bot policy.

    1. If (pages + subcats) == 0
         • delete when no backlinks
         • else replace with redirect stub
    2. Else tidy markup and add/update size‑tag based on pages + subcats.
    """
    members = _cat_member_count(cat_page)

    # === Case 1 : empty category ====================================
    if members == 0:
        if not has_backlinks(cat_page):
            try:
                cat_page.delete(reason="Bot: empty, orphaned category", watch=False)
                print(f"   • deleted empty orphan category [[{cat_page.name}]]")
            except Exception as e:
                print(f"   ! cannot delete [[{cat_page.name}]] – {e}")
            return
        # has backlinks → convert to redirect stub -------------------
        redirect_stub = (
            "#redirect[[en:{{subst:PAGENAME}}]]\n"
            "[[Category:redirect categories]]\n"
        )
        if safe_save(cat_page, redirect_stub, "Bot: empty category redirect"):
            print(f"   • redirected empty category [[{cat_page.name}]]")
        return  # finished with empty category

    # === Case 2 : category with members =============================
    original = cat_page.text()
    cleaned  = original.replace('#', '')  # strip literal '#'

    # drop unwanted cats and old size tag
    for bad in REMOVE_CATS:
        cleaned = re.sub(rf"\[\[Category:{re.escape(bad)}\]\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = META_TAG_RE.sub("", cleaned).rstrip()

    # append / update size tag
    size_tag = f"[[Category:Categories with {members} members]]"
    if size_tag not in cleaned:
        cleaned += "\n" + size_tag + "\n"

    # save if modified
    if cleaned != original:
        if safe_save(cat_page, cleaned, f"Bot: tidy & size tag ({members} members)"):
            print(f"   • tidied [[{cat_page.name}]] ({members} members)")


# ─── MAIN ───────────────────────────────────────────────────

def main():
    """Sweep every main‑namespace page, then all categories."""

    # —— Phase 1 – full mainspace sweep ————————————————
    print("—— Mainspace sweep ————————————————————————————")
    for idx, page in enumerate(site.allpages(namespace=0, start=''), 1):
        print(f"{idx} [[{page.name}]]")
        process_page(page)
        time.sleep(1)

    # —— Phase 2 – category maintenance ————————————————
    print("—— Category maintenance ——————————————————————————")
    for idx, cat in enumerate(site.allpages(namespace=14), 1):
        tidy_category(cat)
        time.sleep(1)

    print("Done!")


if __name__ == "__main__":
    main()
