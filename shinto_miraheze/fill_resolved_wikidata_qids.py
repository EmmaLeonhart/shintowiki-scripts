#!/usr/bin/env python3
"""
fill_resolved_wikidata_qids.py
==============================
Part 3b of the interlanguage-resolution operation (Emma, 2026-06-07). Local
only: edits git_synced/ files; the git sync writes them back to the wiki.

Reads build_wikidata_resolution_csv.out.csv and, for every row that is a
high-confidence safe fill, writes the QID into that page's {{wikidata link}}
slot-1 in its git_synced/ file.

Safe fill = match_type == "exact-label" AND no overlap_p11250. Those are the
rows where the Wikidata item's label exactly equals the page's own
native-language interlanguage target and no other shinto page already claims
that QID. Everything else is left untouched for manual handling:
  * overlaps  -> MERGE pass (prefer "Jingū" over "...Shrine"); both pages synced.
  * search-hit -> needs eyeball confirmation.
  * no-hit / throttled -> needs an article created, or a re-run.

Only the slot-1 QID is set; existing interlanguage pairs and named params are
preserved (the wikidata_lookup op will refresh the pairs from the item's
sitelinks on its next run).
"""

import csv
import io
import os
import re
import sys
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GIT_SYNCED_DIR = os.path.join(REPO_ROOT, "git_synced")
CSV_PATH = os.path.join(SCRIPT_DIR, "build_wikidata_resolution_csv.out.csv")

WD_LINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}", re.IGNORECASE)
_FORBIDDEN = set('<>:"/\\|?*')


def title_to_filename(title):
    out = []
    for c in title:
        out.append(f"%{ord(c):02X}" if (c in _FORBIDDEN or c == "%") else c)
    return "".join(out) + ".wiki"


def set_qid(template_body, qid):
    """template_body is the text after '{{wikidata link' up to '}}' (the
    leading '|...' group). Returns a rebuilt '{{wikidata link|...}}' with slot-1
    set to qid, preserving pairs and named params and their order."""
    parts = [p for p in template_body.split("|")[1:]]
    named, positional = [], []
    for p in parts:
        (named if "=" in p else positional).append(p)
    # slot-1 is the QID; set it, keep the rest of the positionals (the pairs)
    if positional:
        positional[0] = qid
    else:
        positional = [qid]
    body = "|".join(positional + named)
    return "{{wikidata link|" + body + "}}"


def main():
    apply = "--apply" in sys.argv
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    filled = skipped = missing = already = 0
    for r in rows:
        if r["match_type"] != "exact-label" or r["overlap_p11250"]:
            skipped += 1
            continue
        qid = r["best_qid"]
        if not qid:
            skipped += 1
            continue
        path = os.path.join(GIT_SYNCED_DIR, title_to_filename(r["title"]))
        if not os.path.exists(path):
            missing += 1
            print(f"MISSING file: {r['title']}")
            continue
        text = open(path, encoding="utf-8").read()
        m = WD_LINK_RE.search(text)
        if not m:
            missing += 1
            print(f"NO TEMPLATE: {r['title']}")
            continue
        # already has a QID in slot 1?
        pos = [p.strip() for p in m.group(1).split("|")[1:] if "=" not in p]
        if pos and pos[0]:
            already += 1
            continue
        new_tmpl = set_qid(m.group(1), qid)
        new_text = text[:m.start()] + new_tmpl + text[m.end():]
        if apply:
            open(path, "w", encoding="utf-8").write(new_text)
        filled += 1
        print(f"{'FILL' if apply else 'DRY '} {r['title'][:40]:40} -> {qid}")

    print(f"\n{'APPLIED' if apply else 'DRY-RUN'}: filled={filled} "
          f"skipped(not-safe)={skipped} already-had-qid={already} missing={missing}")


if __name__ == "__main__":
    main()
