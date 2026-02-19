#!/usr/bin/env python3
"""
purge_tier0_categories.py – tag-checked & resilient
Remove a Tier-0 category only if its own wikitext contains
[[Category:Tier 0 Categories]] – and skip any member titles that
trigger API glitches.
"""
import re, time, urllib.parse, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ─── CONFIG ─────────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
PARENT_CAT = "Tier 0 Categories"

THROTTLE  = 0.4
UA        = {"User-Agent": "tier0-purge/1.2 (User:Immanuelle)"}

TAG_RX  = re.compile(r"\[\[\s*Category:\s*Tier 0 Categories\b", re.I)
CAT_PAT = r"\[\[\s*Category:{name}(\s*\|[^\]]*)?]]"

# ─── HELPERS ────────────────────────────────────────────────────────
def cat_regex(name: str) -> re.Pattern:
    fuzzy = re.escape(name).replace(r"\ ", "[ _]")
    return re.compile(CAT_PAT.format(name=fuzzy), re.I)

def safe_page(site, title: str):
    """Return mwclient.Page or None if the title makes the API unhappy."""
    try:
        return site.pages[title]
    except (InvalidPageTitle, KeyError, APIError):
        print(f"    ! API refused title: {title!r} – skipped")
        return None

def strip_cat(page: mwclient.page, rex: re.Pattern, name: str):
    try:
        text = page.text()
    except APIError:
        return
    new, n = rex.subn("", text)
    if n:
        try:
            page.save(new,
                      summary=f"Bot: remove obsolete category {name}",
                      minor=True)
            print(f"    • cleaned {page.name}")
        except APIError as e:
            print(f"    ! save failed on {page.name}: {e.code}")
        time.sleep(THROTTLE)

# ─── MAIN ──────────────────────────────────────────────────────────
def main():
    host = urllib.parse.urlparse(API_URL)
    site = mwclient.Site(host.netloc,
                         path=host.path.rsplit("/api.php",1)[0] + "/",
                         clients_useragent=UA["User-Agent"])
    site.login(USERNAME, PASSWORD)
    print("Logged in – scanning Tier-0 sub-categories…")

    subs = site.api(action="query", list="categorymembers",
                    cmtitle=f"Category:{PARENT_CAT}", cmtype="subcat",
                    cmlimit="max", format="json")["query"]["categorymembers"]

    for entry in subs:
        full     = entry["title"]          # e.g. Category:Foo
        cat_name = full.split(":",1)[1]
        cat_page = site.pages[full]

        try:
            wikitext = cat_page.text()
        except APIError:
            continue
        if not TAG_RX.search(wikitext):
            print(f"\n→ {cat_name}  • no explicit Tier-0 tag – skipped")
            continue

        print(f"\n→ {cat_name}  • processing…")
        rex = cat_regex(cat_name)

        # strip category from every member (pages / subcats / files)
        cmc = None
        while True:
            prm = {"action":"query","list":"categorymembers","cmtitle":full,
                   "cmtype":"page|subcat|file","cmlimit":"max","format":"json"}
            if cmc: prm["cmcontinue"] = cmc
            data = site.api(**prm)
            for mem in data["query"]["categorymembers"]:
                pg = safe_page(site, mem["title"])
                if pg:
                    strip_cat(pg, rex, cat_name)
            cmc = data.get("continue", {}).get("cmcontinue")
            if not cmc:
                break

        # delete the now-empty category page
        try:
            cat_page.delete(reason="Bot: delete empty Tier-0 category",
                            watch=False)
            print("    • category deleted")
        except APIError as e:
            print("    ! delete failed:", e.code)
        time.sleep(THROTTLE)

    print("\nFinished purging explicitly-tagged Tier-0 categories.")

if __name__ == "__main__":
    main()
