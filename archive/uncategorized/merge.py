#!/usr/bin/env python3
"""
category_merge_bot_v2.py – merge one category into another (v2.5)
-----------------------------------------------------------------
**What’s new in v2.5**

1. **Member‑count sanity check** – The bot now prints how many pages it
   thinks belong to the old category *before* doing anything else.
2. **Reliable member query** – Instead of `cat_page.members()`, which can
   silently return nothing if the category is huge or cached, we now hit
   the API directly (`list=categorymembers`) so we *always* get the full
   list (up to 5 000 per request, with automatic paging).
3. **Early abort** if the member list comes back empty – prints a warning
   and exits so you can debug rather than doing all the move work for
   nothing.

Run like:
    python category_merge_bot_v2.py "Place in Egyptian Mythology" \
                                    "Places in Egyptian Mythology"
"""
import os
import re
import sys
import urllib.parse
from typing import List, Tuple

import mwclient
from mwclient.errors import APIError

SUMMARY = "Merge [[Category:{old}]] into [[Category:{new}]] via bot"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def normalise(title: str) -> str:
    """Return canonical `Category:Foo Bar` with spaces, no underscores."""
    title = title.replace("_", " ").strip()
    return title if title.lower().startswith("category:") else f"Category:{title}"


def get_site() -> mwclient.Site:
    api_url = os.environ.get("MW_API_URL")
    if not api_url:
        sys.exit("Set MW_API_URL, MW_USERNAME, MW_PASSWORD in env.")
    parsed = urllib.parse.urlparse(api_url)
    site = mwclient.Site(parsed.netloc, path=parsed.path.rsplit("/api.php", 1)[0] + "/")
    site.login(os.environ.get("MW_USERNAME"), os.environ.get("MW_PASSWORD"))
    return site

# ---------------------------------------------------------------------------
# Category member fetch (robust)
# ---------------------------------------------------------------------------

def fetch_members(site: mwclient.Site, cat_title: str) -> List[mwclient.Page]:
    """Return *all* pages in a category using raw API paging."""
    members: List[mwclient.Page] = []
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat_title,
            "cmlimit": "5000",
            "cmprop": "title|type",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        data = site.api(**params)
        for m in data["query"]["categorymembers"]:
            members.append(site.pages[m["title"]])
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
    return members

# ---------------------------------------------------------------------------
# Replacement regex (unchanged from v2.4)
# ---------------------------------------------------------------------------

def _build_fuzzy_pattern(title: str) -> str:
    parts = [re.escape(p) for p in title.split(" ") if p]
    return r"[ _\s]*".join(parts)


def _cat_regex(old: str) -> re.Pattern:
    ns = r"(?:(?:[Cc]ategor(?:y|ie)))"
    return re.compile(
        fr"\[\[\s*{ns}\s*:\s*{_build_fuzzy_pattern(old)}\s*(\|[^]]*)?]]",
        re.IGNORECASE,
    )


def replace_category_link(text: str, old: str, new: str) -> Tuple[str, int]:
    regex = _cat_regex(old)
    return regex.subn(lambda m: f"[[Category:{new}{m.group(1) or ''}]]", text)

# ---------------------------------------------------------------------------
# Member processing
# ---------------------------------------------------------------------------

def process_members(site: mwclient.Site, pages: List[mwclient.Page], old: str, new: str):
    skipped, unchanged = [], []
    for page in pages:
        print(f"• {page.name}")
        try:
            text = page.text()
        except Exception as e:
            print(f"   !! failed to fetch text: {e}")
            skipped.append(page.name)
            continue

        new_text, n = replace_category_link(text, old, new)
        if n == 0:
            unchanged.append(page.name)
            print("   ▸ no match found")
            continue
        try:
            page.save(new_text, summary=SUMMARY.format(old=old, new=new))
            print(f"   ▸ replaced {n} link(s)")
        except APIError as e:
            print(f"   !! API error: {e}")
            skipped.append(page.name)

    if unchanged:
        print("Pages with *no* replacement (check why):")
        for t in unchanged:
            print("   -", t)
    if skipped:
        print("Skipped (protected/error):")
        for t in skipped:
            print("   -", t)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python category_merge_bot_v2.py 'Old' 'New'")

    old_cat = normalise(sys.argv[1]).removeprefix("Category:")
    new_cat = normalise(sys.argv[2]).removeprefix("Category:")

    site = get_site()
    old_title = f"Category:{old_cat}"
    new_title = f"Category:{new_cat}"

    old_page = site.pages[old_title]
    if not old_page.exists:
        sys.exit(f"Old category [[{old_title}]] does not exist!")

    print("Fetching category members …", end=" ")
    members = fetch_members(site, old_title)
    print(f"{len(members)} page(s)")

    if not members:
        sys.exit("Nothing to do – category is empty.")

    # Prepare move/merge
    reason = SUMMARY.format(old=old_cat, new=new_cat)
    new_page = site.pages[new_title]
    if new_page.exists:
        print(f"Deleting existing target {new_title} …")
        new_page.delete(reason=reason, watch=False, oldimage=False)

    print(f"Moving {old_title} → {new_title} …")
    old_page.move(new_title, reason=reason, move_talk=True, noredirect=True)

    try:
        site.api("undelete", title=new_title, reason=reason, token=site.get_token("csrf"))
    except APIError as e:
        if e.code != "cantundelete":
            raise

    process_members(site, members, old_cat, new_cat)
    print("Done ✔️")


if __name__ == "__main__":
    main()
