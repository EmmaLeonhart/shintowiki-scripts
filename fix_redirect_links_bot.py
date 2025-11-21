#!/usr/bin/env python3
"""
fix_redirect_links_bot.py
=========================
For each page title in pages.txt (canonical pages):

 1. Find every redirect page pointing to it.
 2. For each such redirect, fetch all pages that link to the redirect.
 3. In each linking page:
      • Bare [[Redirect]] → [[Canonical|Redirect]]
      • [[Redirect|Label]] → [[Canonical|Label]]
      • Inside {{ill|…}} blocks:
          |Redirect|     → |Canonical|lt=Redirect|
          |Redirect}}    → |Canonical|lt=Redirect}}
          =Redirect|     → =Canonical|lt=Redirect|
          =Redirect}}    → =Canonical|lt=Redirect}}
 4. Save with “Bot: fix redirect” summary.

Configure your credentials & `pages.txt`, then run:
    python fix_redirect_links_bot.py
"""
import os, sys
import time
import re
import mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0  # seconds between edits

# ─── LOGIN ──────────────────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}\n")

# ─── HELPERS ────────────────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").close()
        print(f"Created empty {path}; fill it with one title per line and re-run.")
        sys.exit()
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def safe_save(page, new_text, summary):
    """Save if changed, handle conflicts gracefully."""
    try:
        old = page.text()
    except Exception:
        print(f"   ! could not fetch text for [[{page.name}]]; skipping")
        return False
    if old == new_text:
        return False
    try:
        page.save(new_text, summary=summary)
        return True
    except APIError as e:
        if e.code == "editconflict":
            print(f"   ! edit conflict on [[{page.name}]]; skipped")
            return False
        print(f"   ! APIError on [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"   ! error saving [[{page.name}]]: {e}")
    return False

def fix_ill_block(block, rd, canonical):
    """
    Within a single {{ill|…}} block, locate any bare
      |Redirect…|  or |Redirect…}}  or =Redirect…|  or =Redirect…}}
    and replace with
      |Canonical|lt=Redirect…|   or   |Canonical|lt=Redirect…}}
      =Canonical|lt=Redirect…|   or   =Canonical|lt=Redirect…}}
    """
    esc = re.escape
    # Case-insensitive replaces:
    #   |RD…(?=[|}]) → |CAN|lt=RD… 
    block = re.sub(
        rf"(?i)\|{esc(rd)}(?=(\||\}}))",
        f"|{canonical}|lt={rd}",
        block
    )
    #   =RD…(?=[|}]) → =CAN|lt=RD…
    block = re.sub(
        rf"(?i)={esc(rd)}(?=(\||\}}))",
        f"={canonical}|lt={rd}",
        block
    )
    return block

# ─── MAIN LOOP ──────────────────────────────────────────────────────
def main():
    canonical_titles = load_titles(PAGES_FILE)
    for idx, canonical in enumerate(canonical_titles, 1):
        print(f"{idx}/{len(canonical_titles)}: Fixing links → [[{canonical}]]")
        can_page = site.pages[canonical]
        if not can_page.exists:
            print(f"  ! [[{canonical}]] does not exist; skipping.\n")
            continue

        # 1) gather all redirects to the canonical page
        redirects = []
        try:
            for rd in can_page.redirects(limit=None):
                redirects.append(rd.name)
        except Exception:
            data = site.api("query", prop="redirects", titles=canonical, rdlimit="max")
            for p in data["query"]["pages"].values():
                for rd in p.get("redirects", []):
                    redirects.append(rd["title"])

        if not redirects:
            print("  (no redirects to fix)\n")
            continue

        # 2) for each redirect, fix all backlinks
        for rd_title in redirects:
            print(f"  → Redirect [[{rd_title}]] → [[{canonical}]]")
            # Plain-link regex, case-insensitive
            link_pat = re.compile(
                rf"\[\[\s*{re.escape(rd_title)}\s*(?:\|([^\]]+))?\]\]",
                re.IGNORECASE
            )

            # fetch backlinks
            try:
                backlnks = list(site.pages[rd_title].backlinks(limit=None))
            except Exception:
                backs = site.api(
                    "query", list="backlinks",
                    bltitle=rd_title, blfilterredir="nonredirects",
                    bllimit="max"
                )
                backlnks = [site.pages[b["title"]] for b in backs["query"]["backlinks"]]

            for lp in backlnks:
                if lp.redirect:
                    # skip pages that are themselves redirects
                    continue
                try:
                    text = lp.text()
                except Exception:
                    print(f"    ! could not fetch [[{lp.name}]]; skipping")
                    continue

                new = text
                # A) fix bare or piped links → [[CAN|label]]
                def repl_link(m):
                    label = m.group(1) or rd_title
                    return f"[[{canonical}|{label}]]"
                new = link_pat.sub(repl_link, new)

                # B) fix inside any {{ill|…}} block
                if "{{ill|" in new:
                    new = re.sub(
                        r"(\{\{ill\|.*?\}\})",
                        lambda m: fix_ill_block(m.group(1), rd_title, canonical),
                        new,
                        flags=re.DOTALL
                    )

                if new != text:
                    summary = f"Bot: fix redirect [[{rd_title}]] → [[{canonical}]]"
                    print(f"    • updating [[{lp.name}]]")
                    if safe_save(lp, new, summary):
                        time.sleep(THROTTLE)
            print()
        print()

    print("All done.")

if __name__ == "__main__":
    main()
