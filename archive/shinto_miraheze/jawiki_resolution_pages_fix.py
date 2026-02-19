#!/usr/bin/env python3
"""
jawiki_resolution_pages_fix.py
==============================

* If **resolutionpages.txt** exists → process titles from that file.
  Otherwise iterate every member of **[[Category:Jawiki resolution pages]]**
  using API continuation (no big upfront member list).

For each resolution page P (title == Japanese title):
1. **Reconstruct full history** into the live page:
   * Fetch every revision (oldest → newest).
   * Build a document like::

        [[Jaw:...]]  ← (plain link to the Japanese title)
        == 2025‑05‑18 12:34 ==
        <wikitext of that revision>
        == 2025‑05‑18 12:35 ==
        <next revision> …

2. Count `{{ill|…}}` templates in the final version; append a category
   `[[Category:jawiki resolution pages |<count>]]` (like the original bot).

3. Decide whether the page is **obsolete**:
   * For every `{{ill|…}}` on the page, find the *local* link target field
     (parameter `1=` or first positional after label).
   * If *all* ILLs point to the **same, non‑redirect, existing** page on the
     local wiki → delete P.

4. If not deleted: move P **without redirect** to
   `Jawiki resolution:<Japanese title>` (segregated namespace).

Requires delete, move, and edit rights.
"""
import os, re, time, urllib.parse, mwclient, requests
from mwclient.errors import APIError, InvalidPageTitle
from datetime import datetime, timezone

# ─── CONFIG ─────────────────────────────────────────────────────────
SITE_URL  = "shinto.miraheze.org"; SITE_PATH = "/w/"
USERNAME  = "Immanuelle"; PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE  = 0.4
CAT_NAME  = "Jawiki resolution pages"
LIST_FILE = "resolutionpages.txt"
NS_TARGET = "Jawiki resolution"   # new custom namespace (must exist)

ILL_RE = re.compile(r"\{\{\s*ill\|(.*?)\}\}", re.I | re.S)

# ─── UTILITIES ─────────────────────────────────────────────────────

def parse_ill_target(inner: str) -> str | None:
    """Return the *local link target* for the ILL template."""
    parts = [p.strip() for p in inner.split("|")]
    # collect key=value
    for p in parts:
        if p.startswith("1="):
            return p[2:].strip()
    # otherwise positional: label, lang1, title1 … so first param after label
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def count_ills(text: str) -> int:
    return len(ILL_RE.findall(text))


def reconstruct_history(site, title: str) -> str:
    revs = site.api(action='query', prop='revisions', titles=title,
                    rvprop='timestamp|content', rvslots='main', rvlimit='max',
                    rvdir='newer', format='json')['query']['pages']
    page = next(iter(revs.values()))
    out = [f"[[Ja:{title}]]\n"]
    for rev in page.get('revisions', []):
        ts = datetime.fromisoformat(rev['timestamp'].replace('Z','+00:00'))
        ts_str = ts.astimezone(timezone.utc).strftime('%Y‑%m‑%d %H:%M')
        out.append(f"== {ts_str} ==\n")
        out.append(rev['slots']['main']['*'].rstrip() + "\n")
    return "\n".join(out)


def should_delete(site, text: str) -> bool:
    targets = set()
    for inner in ILL_RE.findall(text):
        t = parse_ill_target(inner)
        if not t:
            return False
        targets.add(t.replace('_',' '))
    if len(targets) != 1:
        return False
    tgt = targets.pop()
    pg = site.pages[tgt]
    return pg.exists and not pg.redirect

def save_page(page: mwclient.page, text: str, summary: str):
    try:
        page.save(text, summary=summary)
        print("    • saved", page.name)
    except APIError as e:
        print("    ! save failed:", e.code)

# ─── ITERATOR OVER PAGES ───────────────────────────────────────────

def pages_to_process(site):
    if os.path.exists(LIST_FILE):
        for ln in open(LIST_FILE, encoding='utf-8'):
            t = ln.strip();
            if t and not t.startswith('#'):
                yield t.replace('_',' ')
    else:
        cont = None
        while True:
            q = {"action":"query","list":"categorymembers",
                 "cmtitle":f"Category:{CAT_NAME}","cmtype":"page",
                 "cmlimit":"max","format":"json"}
            if cont: q['cmcontinue']=cont
            data=site.api(**q)
            for m in data['query']['categorymembers']:
                yield m['title']
            if 'continue' in data:
                cont=data['continue']['cmcontinue']
            else:
                break

# ─── MAIN ──────────────────────────────────────────────────────────

def main():
    site = mwclient.Site(SITE_URL, path=SITE_PATH)
    site.login(USERNAME, PASSWORD)

    for idx, title in enumerate(pages_to_process(site),1):
        print(f"\n{idx}. [[{title}]]")
        pg = site.pages[title]
        if not pg.exists or pg.redirect:
            print("   • missing/redirect – skipped"); continue

        new_text = reconstruct_history(site, title)
        ill_count = count_ills(new_text)
        # remove any old cat line, then add new one
        new_text = re.sub(r"\[\[Category:jawiki resolution pages[^\]]*\]\]","",new_text,flags=re.I).rstrip()
        new_text += f"\n[[Category:{CAT_NAME}|{ill_count}]]\n"

        if should_delete(site, new_text):
            try:
                pg.delete(reason="Bot: obsolete resolution page", watch=False)
                print("   • deleted (all links resolved)")
            except APIError as e:
                print("   ! delete failed", e.code)
            time.sleep(THROTTLE)
            continue

        # save reconstructed content
        save_page(pg, new_text, "Bot: reconstruct full history + recat")
        time.sleep(THROTTLE)

        # move to Jawiki resolution namespace (noredirect)
        target_title = f"{NS_TARGET}:{title}"
        try:
            pg.move(target_title, reason="Bot: move to Jawiki resolution ns",
                    no_redirect=True, move_talk=False)
            print("   • moved →", target_title)
        except APIError as e:
            print("   ! move failed", e.code)
        time.sleep(THROTTLE)
    print("All done.")

if __name__ == '__main__':
    main()
