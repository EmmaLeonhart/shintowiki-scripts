"""
reformat_pages_bot.py (v6)
=========================
Cleans pages listed in pages_reformat.txt by:
1) Keeping any existing non-empty `{{draft categories|…}}` block (first one)
2) Removing any *empty* or whitespace-only draft templates
3) Extracting **other** categories, interwiki links, and comments
4) Removing all draft templates (so empty ones and non-empty ones are removed), but preserving the first non-empty one
5) Reassembling output:
   • The preserved draft block with original categories (if found),
     else a rebuilt one from extracted categories
   • Interwikis (one per line, no blank lines)
   • Comments
6) Collapsing 3+ blank lines to 2

Other logic (login, loop, safe_save) unchanged.
"""

import os
import sys
import time
import re
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL       = 'shinto.miraheze.org'
WIKI_PATH      = '/w/'
USERNAME       = 'Immanuelle'
PASSWORD       = '[REDACTED_SECRET_1]'
PAGES_TXT      = 'pages_reformat.txt'
THROTTLE       = 1.0  # seconds between edits
REMOVE_CATS    = {'qq', 'Qq', 'New', '11'}

# ─── LOGIN ──────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print('Logged in.')

# ─── REGEX RULES ────────────────────────────────────────────────────
CAT_LINK_RE       = re.compile(r"\[\[Category:([^\]|]+)(?:\|[^\]]*)?\]\]", re.IGNORECASE)
IWL_RE            = re.compile(r"\[\[[a-z]{2,}:[^\]]+\]\]")
COMMENT_RE        = re.compile(r"<!--([\s\S]*?)-->")
# all draft templates
ALL_DRAFT_RE      = re.compile(r"(\{\{\s*draft\s+categories\s*\|[\s\S]*?\}\})", re.IGNORECASE)
# empty or whitespace-only
EMPTY_DRAFT_RE    = re.compile(r"\{\{\s*draft\s+categories\s*\|[\s\r\n]*\}\}", re.IGNORECASE)

# ─── HELPERS ────────────────────────────────────────────────────────
def dedupe(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def reformat_text(text):
    # find all draft templates
    drafts = ALL_DRAFT_RE.findall(text)
    # pick first non-empty as keeper
    keeper = None
    for d in drafts:
        if not EMPTY_DRAFT_RE.fullmatch(d):
            keeper = d.strip()
            break
    # remove only empty ones now
    text = EMPTY_DRAFT_RE.sub('', text)
    # extract elements
    cats     = CAT_LINK_RE.findall(text)
    iws      = IWL_RE.findall(text)
    comments = COMMENT_RE.findall(text)
    # remove original draft templates (all)
    text = ALL_DRAFT_RE.sub('', text)
    # remove cats, iws, comments
    text = CAT_LINK_RE.sub('', text)
    text = IWL_RE.sub('', text)
    text = COMMENT_RE.sub('', text)
    # dedupe + filter unwanted
    cats = [c for c in dedupe(cats) if c not in REMOVE_CATS]
    iws  = dedupe(iws)
    # build draft block
    if keeper:
        draft_block = keeper
    elif cats:
        draft_block = '{{draft categories|\n' + '\n'.join(f'[[Category:{c}]]' for c in cats) + '\n}}'
    else:
        draft_block = None
    # assemble parts
    parts = []
    if draft_block:
        parts.append(draft_block)
    if iws:
        parts.append('\n'.join(iws))
    if comments:
        parts.append(''.join(f'<!--{c}-->' for c in comments))
    # assemble text
    body = text.strip()
    if parts:
        new_text = body + '\n\n' + '\n\n'.join(parts) + '\n'
    else:
        new_text = body + '\n'
    # collapse blank lines
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)
    return new_text


def safe_save(page, text, summary):
    if not page.exists:
        print(f"   • skipped [[{page.name}]] (deleted)")
        return False
    try:
        curr = page.text()
    except:
        curr = None
    if curr is not None and curr.rstrip() == text.rstrip():
        return False
    try:
        page.save(text, summary=summary)
        return True
    except APIError as e:
        if getattr(e,'code','')=='editconflict':
            print(f"   ! edit conflict on [[{page.name}]]")
            return False
        raise
    except Exception as e:
        print(f"   ! save failed on [[{page.name}]] – {e}")
        return False

# ─── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    if not os.path.exists(PAGES_TXT):
        open(PAGES_TXT,'w').close(); print(f"Created {PAGES_TXT}"); sys.exit()
    with open(PAGES_TXT, 'r', encoding='utf-8', errors='ignore') as fh:
        titles = [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]
    for idx, title in enumerate(titles,1):
        print(f"{idx}/{len(titles)} — [[{title}]]")
        pg = site.pages[title]
        if not pg.exists:
            print(f"   ! [[{title}]] missing")
            continue
        orig = pg.text(); new = reformat_text(orig)
        if new.strip()!=orig.strip():
            if safe_save(pg,new,'Bot: cleanup/reformat'):
                print(f"   • saved [[{title}]]")
        time.sleep(THROTTLE)
    print('Done!')

if __name__=='__main__': main()
