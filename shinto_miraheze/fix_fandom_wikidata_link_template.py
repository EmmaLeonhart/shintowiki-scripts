#!/usr/bin/env python3
"""
fix_fandom_wikidata_link_template.py
=====================================
One-shot idempotent fix for Template:Wikidata link on shinto.fandom.com.

The miraheze version of this template uses ``{{q|{{{1}}}}}`` which resolves
to Template:Wikidata entity link on fandom. That template relies on
``[[d:Special:EntityPage/...]]`` (the ``d:`` interwiki prefix is not
configured on fandom) plus ``{{#invoke:wd|label|...}}`` (Module:Wd cannot
access Wikibase data on fandom). The result is a Lua script error and a
broken/missing Wikidata link.

This script replaces the broken template on fandom with a wikitext-only shim
that emits a plain HTTPS external link:
  [https://www.wikidata.org/wiki/{{{1}}} {{{1}}}]

The miraheze-side template is NOT touched; only fandom is edited.
The script is idempotent: it reads the current fandom wikitext, compares
it to the desired shim, and only saves if they differ.
"""

import hashlib
import io
import os
import sys

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FAN_HOST = "shinto.fandom.com"
FAN_PATH = "/"
FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")
USER_AGENT = "FandomCleanupBot/1.0 (User:EmmaBot; shinto.fandom.com cleanup)"

TITLE = "Template:Wikidata link"

# Canonical fandom-side shim.  No Lua, no interwiki prefixes; plain HTTPS URL.
FANDOM_SHIM = """\
{{tmbox
 |name=wikidata-entry
 |type=notice
 |image=[[File:Wikidata-logo.svg|30px]]
 |small=yes
 |smallimage=[[File:Wikidata-logo.svg|20px]]
 |smalltext=This {{pagetype}} is linked to its entry on [[Wikidata]]: [https://www.wikidata.org/wiki/{{{1}}} {{{1}}}].
}}<includeonly>
</includeonly><noinclude>
{{documentation}}
[[Category:Templates]]
[[Category:Templates fixed with noinclude]]
</noinclude>
"""


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def main() -> int:
    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit fandom (default: dry-run).")
    parser.add_argument("--run-tag", default="",
                        help="Wiki-formatted run tag link for edit summary.")
    args = parser.parse_args()

    print(f"Logging in to {FAN_HOST}...")
    fan = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    fan.connection.timeout = 120
    fan.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print("  OK")

    result = fan.api(
        "query",
        prop="revisions",
        rvprop="ids|content",
        rvslots="main",
        rvlimit=1,
        titles=TITLE,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages or pages[0].get("missing"):
        print(f"ERROR: {TITLE} does not exist on fandom.")
        return 1

    page_data = pages[0]
    revs = page_data.get("revisions") or []
    current_text = revs[0].get("slots", {}).get("main", {}).get("content", "") if revs else ""
    current_revid = revs[0].get("revid") if revs else None

    if sha1(current_text) == sha1(FANDOM_SHIM):
        print(f"Already up to date (revid {current_revid}). No edit needed.")
        return 0

    print(f"Current revid: {current_revid}")
    print(f"Current sha1:  {sha1(current_text)}")
    print(f"Desired sha1:  {sha1(FANDOM_SHIM)}")
    print("Template needs updating.")

    if not args.apply:
        print("[DRY-RUN] Would save fandom Template:Wikidata link with HTTPS-URL shim.")
        return 0

    summary = (
        "Replace {{q|...}} (Wikidata entity link, broken on fandom: no d: interwiki "
        "and Lua Wikibase access unavailable) with plain HTTPS URL "
        "https://www.wikidata.org/wiki/{{{1}}}; drop non-functional interwiki links"
    )
    if args.run_tag:
        summary += f" {args.run_tag}"

    page = fan.pages[TITLE]
    save_result = page.save(FANDOM_SHIM, summary=summary)
    new_revid = (save_result or {}).get("newrevid")
    if new_revid is None:
        r2 = fan.api("query", prop="revisions", rvprop="ids", rvlimit=1,
                     titles=TITLE, formatversion="2")
        p2 = (r2.get("query", {}).get("pages", []) or [{}])[0]
        rv2 = (p2.get("revisions") or [{}])[0]
        new_revid = rv2.get("revid")
    print(f"Saved {TITLE} -> new revid {new_revid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
