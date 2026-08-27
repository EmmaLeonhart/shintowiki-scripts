#!/usr/bin/env python3
"""
remove_wrong_wikidata_links.py
==============================
One-off. Removes ``{{wikidata link|...}}`` from four pages that carry a QID which
is not their subject. Emma's call, 2026-08-27, asked with the premise established
first: *"Remove the link from all four."*

Why removal and not a repoint
-----------------------------
Each page is CORRECT; only its link is wrong. There is nothing to repoint to —
searched Wikidata on 2026-08-27 and no suitable item exists for any of the four:

===============================  =========== ==========================================
page                             wrong QID   what the QID actually is
===============================  =========== ==========================================
``Template:Ichinomiya``          Q1656379    the concept "shrine with the highest rank
                                             in a province". A navbox is not the
                                             concept it navigates. No Wikimedia-template
                                             item exists for it.
``Template:Sōja shrines``        Q1107129    the concept "type of shrine where the kami
                                             of a region are grouped". Same shape.
``Benzaiten shrines``            Q818468     the water DEITY. The page is a list —
                                             "Major Shrines Dedicated to Benzaiten".
                                             Its own link even targets the jawiki
                                             SECTION 弁才天#弁才天を祀る主な神社, i.e. a
                                             section, not an entity. No class/list item
                                             exists.
``Hime Shrine``                  Q22070227   the GODDESS Himegami. The page is a list of
                                             shrines dedicated to her. Wikidata has
                                             several distinct "Hime Shrine" items and
                                             this is none of them.
===============================  =========== ==========================================

Safety
------
The expected QID is recorded per page and the removal only fires when the page's
current link still carries it. If someone has already repointed or removed it, the
page is skipped rather than edited — so a re-run cannot undo a later fix, and this
script is idempotent.

Only the ``{{wikidata link}}`` call is removed. Nothing else on the page is
touched; these pages are otherwise fine.

Standard flags: ``--apply`` (default dry-run), ``--max-edits``, ``--run-tag``.
Gated on the miraheze lockout in code, so a manual run is covered and not only CI.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import os
import re
import subprocess
import sys
import time

import mwclient
from wiki_login import login_with_retry

from shinto_miraheze.user_agent import USER_AGENT

if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

# page -> the wrong QID it is expected to still carry
TARGETS = {
    "Template:Ichinomiya": "Q1656379",
    "Template:Sōja shrines": "Q1107129",
    "Benzaiten shrines": "Q818468",
    "Hime Shrine": "Q22070227",
}

WDLINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)[^{}]*\}\}\n?", re.IGNORECASE)


def strip_link(text: str, expected_qid: str):
    """Return (new_text, removed_qid) or (None, found_qid_or_None) if not applicable."""
    match = WDLINK_RE.search(text)
    if not match:
        return None, None
    found = match.group(1).upper()
    if found != expected_qid.upper():
        return None, found
    return text[:match.start()] + text[match.end():], found


def lockout_blocks_us() -> bool:
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_edit_allowed.py")
    if not os.path.isfile(checker):
        return False
    return subprocess.call([sys.executable, checker]) != 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually save (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=len(TARGETS),
                        help=f"Cap per run (default {len(TARGETS)} — there are only that many).")
    parser.add_argument("--run-tag", required=True,
                        help="Edit-summary suffix linking back to the CI run.")
    args = parser.parse_args()

    if lockout_blocks_us():
        print("SKIPPED: miraheze editing is locked. Nothing attempted.")
        return

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    edited = skipped = errors = 0
    for title, expected in TARGETS.items():
        if edited >= args.max_edits:
            print(f"Budget of {args.max_edits} reached, stopping.")
            break
        try:
            page = site.pages[title]
            if not page.exists:
                print(f"  SKIP {title!r}: page does not exist")
                skipped += 1
                continue
            text = page.text()
        except Exception as e:
            print(f"  ERROR {title!r}: {e}")
            errors += 1
            continue

        new_text, found = strip_link(text, expected)
        if new_text is None:
            reason = ("no {{wikidata link}} present" if found is None
                      else f"link now points at {found}, not the expected {expected}")
            print(f"  SKIP {title!r}: {reason} — already handled, leaving alone")
            skipped += 1
            continue

        summary = (f"Bot: remove {{{{wikidata link}}}} to {expected} — "
                   f"this page is not that item {args.run_tag}").strip()
        if not args.apply:
            print(f"  [DRY] would remove {expected} from {title!r}")
            edited += 1
            continue
        try:
            page.save(new_text, summary=summary)
            print(f"  REMOVED {expected} from {title!r}")
            edited += 1
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"  ERROR saving {title!r}: {e}")
            errors += 1

    print()
    print(f"Edited: {edited}   Skipped: {skipped}   Errors: {errors}")


if __name__ == "__main__":
    main()
