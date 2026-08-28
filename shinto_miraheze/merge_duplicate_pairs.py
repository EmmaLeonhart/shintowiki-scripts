#!/usr/bin/env python3
"""
merge_duplicate_pairs.py
========================
Merges a Japanese-TITLED page into its English-titled twin and redirects the
former, for the pairs where the Japanese-titled page genuinely holds more.

Emma, 2026-08-28: *"Physically merge the content of the Japanese into the English
and redirect the Japanese so qid shit is resolved."* And on pacing, offered a batch
run: *"I do them, one per work-loop tick."* So ``MERGES`` is worked one entry per
tick, not drained.

What these pages actually are
-----------------------------
⚠ The Japanese-TITLED pages are ENGLISH articles. Their headings read ``Overview``,
``Name``, ``Ancestry``, ``Clan``, ``Territory`` — they are English translations of a
jawiki source sitting at a Japanese title, beside a second translation at an English
title. So "merge the Japanese into the English" is not a translation job; it is
choosing which of two English translations survives, and keeping what only one has.

Measured across the twelve candidates on 2026-08-28, ten of them have an English
page of comparable or greater size (0.4x-1.5x) carrying ``{{translated page}}`` —
those are already translated and need only the redirect. Only two have
substantially more on the Japanese side, and they are the ones here.

The safety gate
---------------
``merge_text`` REFUSES unless the source is at least ``MIN_SOURCE_RATIO`` times the
target. That is the whole premise of this script: it replaces the target's body, so
if the target were the fuller page the merge would destroy content. The ratio is
checked against the LIVE pages at run time, not against what was true when the pair
was added here — a page can grow between then and now.

Categories are UNIONED, never replaced, and the target's ``{{wikidata link}}`` is
kept. Those are the two things the target legitimately owns.

Standard flags: ``--apply`` (default dry-run), ``--max-merges`` (default 1, matching
one-per-tick), ``--run-tag``. Gated on the miraheze lockout in code.
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

# The source must be at least this many times the target's size. Below it, the
# premise fails and the merge is refused rather than guessed at.
MIN_SOURCE_RATIO = 2.0

# (Japanese-titled source, English-titled target). Only pairs where the source
# genuinely holds more; everything else is a redirect job, not a merge.
MERGES = [
    ("科野国造", "Shinano no Kuni no Miyatsuko"),
    ("国造", "Kuni no miyatsuko"),
]

CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:\s*([^\]|]+?)\s*(?:\|[^\]]*)?\]\]", re.IGNORECASE)
WDLINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|[^{}]*\}\}", re.IGNORECASE)
REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE)


def strip_categories(text: str) -> str:
    return CATEGORY_RE.sub("", text)


def merge_text(source: str, target: str):
    """Return (merged_text, note) or (None, refusal_reason).

    The source body wins, because this runs only where the source is the fuller
    page. What the target keeps is what it legitimately owns: its categories, which
    are unioned rather than replaced, and its {{wikidata link}}.
    """
    if REDIRECT_RE.match(source):
        return None, "source is already a redirect"
    if REDIRECT_RE.match(target):
        return None, "target is a redirect, not an article"
    if len(target) and len(source) < len(target) * MIN_SOURCE_RATIO:
        return None, (f"source is {len(source)}b against target {len(target)}b — "
                      f"below the {MIN_SOURCE_RATIO}x gate, so the premise that the "
                      f"source is fuller does not hold")

    cats = []
    for text in (target, source):          # target's categories first, then new ones
        for c in CATEGORY_RE.findall(text):
            if c not in cats:
                cats.append(c)

    body = strip_categories(source).rstrip()
    # Keep the TARGET's wikidata link; drop the source's so the page carries one.
    target_link = WDLINK_RE.search(target)
    body = WDLINK_RE.sub("", body).rstrip()
    parts = [body, ""]
    if target_link:
        parts += [target_link.group(0), ""]
    parts += [f"[[Category:{c}]]" for c in cats]
    merged = "\n".join(parts) + "\n"
    note = (f"source {len(source)}b -> target was {len(target)}b, "
            f"{len(cats)} categories unioned")
    return merged, note


def lockout_blocks_us() -> bool:
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_edit_allowed.py")
    if not os.path.isfile(checker):
        return False
    return subprocess.call([sys.executable, checker]) != 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actually save (default: dry-run).")
    parser.add_argument("--max-merges", type=int, default=1,
                        help="Cap per run (default 1 — Emma asked for one per work-loop tick).")
    parser.add_argument("--run-tag", default="", help="Edit-summary suffix linking back to the run.")
    args = parser.parse_args()

    if lockout_blocks_us():
        print("SKIPPED: miraheze editing is locked. Nothing attempted.")
        return

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    merged = refused = errors = 0
    for src_title, dst_title in MERGES:
        if merged >= args.max_merges:
            print(f"Cap of {args.max_merges} reached, stopping. Remaining pairs run next tick.")
            break
        try:
            src, dst = site.pages[src_title], site.pages[dst_title]
            if not src.exists:
                print(f"  SKIP {src_title!r}: source does not exist")
                refused += 1
                continue
            if not dst.exists:
                print(f"  SKIP {dst_title!r}: target does not exist")
                refused += 1
                continue
            src_text, dst_text = src.text(), dst.text()
        except Exception as e:
            print(f"  ERROR reading {src_title!r}/{dst_title!r}: {e}")
            errors += 1
            continue

        new_text, note = merge_text(src_text, dst_text)
        if new_text is None:
            print(f"  REFUSED {src_title!r} -> {dst_title!r}: {note}")
            refused += 1
            continue

        print(f"  MERGE {src_title!r} -> {dst_title!r}  ({note})")
        if not args.apply:
            print("    [DRY] would write the target and redirect the source")
            merged += 1
            continue
        try:
            dst.save(new_text,
                     summary=f"Merge content from [[{src_title}]] {args.run_tag}".strip())
            time.sleep(THROTTLE)
            src.save(f"#REDIRECT [[{dst_title}]]\n",
                     summary=f"Merged into [[{dst_title}]] {args.run_tag}".strip())
            time.sleep(THROTTLE)
            print(f"    merged and redirected")
            merged += 1
        except Exception as e:
            print(f"  ERROR saving: {e}")
            errors += 1

    print()
    print(f"Merged: {merged}   Refused: {refused}   Errors: {errors}")


if __name__ == "__main__":
    main()
