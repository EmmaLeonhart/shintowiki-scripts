#!/usr/bin/env python3
"""
remove_wrong_wikidata_links.py
==============================
Removes ``{{wikidata link|...}}`` from pages that should not be claiming the QID
they carry. Two batches, both Emma's call, each asked with the premise established
first rather than as a merge question.

**2026-08-27, four pages whose QID is not their subject** — *"Remove the link from
all four."* Nothing to repoint to; searched Wikidata and no suitable item exists.

**2026-08-28, nine Japanese-named templates duplicating an English twin** — *"Just
drop the QID from the JP ones."* Here the QID is not wrong about the subject, it is
merely claimed twice, so the edit summary says so rather than reusing the first
batch's wording. Redirecting was the alternative and was NOT chosen: both sides are
in live use (警告 3 transclusions against Warning's 70, 和暦 3 against Japanese
year's 394), and a redirect would silently give the English markup to pages that
asked for the Japanese template.

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

# page -> (QID it is expected to still carry, why it should not carry it)
# The reason is not decoration: it becomes the wiki edit summary, and the two
# batches are wrong for DIFFERENT reasons. Reusing one wording for both would put a
# false statement in the page history of nine templates.
NOT_THIS_ITEM = "this page is not that item"
DUPLICATE = "it duplicates the English template of the same name"

TARGETS = {
    # 2026-08-27 — the QID is not this page's subject, and nothing exists to
    # repoint to. A navbox is not the concept it navigates; a list of shrines
    # dedicated to a deity is not the deity.
    "Template:Ichinomiya": ("Q1656379", NOT_THIS_ITEM),
    "Template:Sōja shrines": ("Q1107129", NOT_THIS_ITEM),
    "Benzaiten shrines": ("Q818468", NOT_THIS_ITEM),
    "Hime Shrine": ("Q22070227", NOT_THIS_ITEM),
    # 2026-08-28 — Japanese-named templates duplicating an English twin. The QID is
    # not WRONG about the subject here, it is merely claimed twice, so the summary
    # says that instead. Both sides are in live use, which is why Emma chose
    # dropping the QID over redirecting: a redirect would hand the English markup
    # to pages that asked for the Japanese template.
    "Template:警告": ("Q5528794", DUPLICATE),
    "Template:和暦": ("Q6062619", DUPLICATE),
    "Template:博物館": ("Q6232685", DUPLICATE),
    "Template:誰": ("Q6841435", DUPLICATE),
    "Template:注意": ("Q6176883", DUPLICATE),
    "Template:雑多な内容の箇条書き": ("Q5615163", DUPLICATE),
    "Template:読み仮名": ("Q14334739", DUPLICATE),
    "Template:テーマカテゴリ": ("Q13413959", DUPLICATE),
    "Template:三島由紀夫": ("Q11215212", DUPLICATE),
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
    for title, (expected, reason) in TARGETS.items():
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
                   f"{reason} {args.run_tag}").strip()
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
