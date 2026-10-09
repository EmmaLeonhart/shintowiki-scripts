#!/usr/bin/env python3
"""Build the next browser QuickStatements round into browser_chunks/.

Run by the browser-batch cron once the previous round's batches are all DONE and a fresh
regeneration has landed (Emma, 2026-10-06/08/09: run the rounds "until we are clear of
everything").

1. The previous round finished, so every sequential_misc line it sent has run: move the
   sequential_misc cursor past them (count recorded in browser_chunks/sequential_sent.json
   when that round was built). Without this the whole file went into every round and the
   rounds could never reach 0 lines (2026-10-09).
2. Build the units (site/build_qs_home.build_units, which now sends only the sequential lines
   past the cursor) and pack them into parts of at most 5,000 lines.
3. Replace the part files, start progress.txt over with HEADER, record how many sequential
   lines this round sends.

Prints "<lines> <parts>"; 0 lines means clear (nothing is written then).

    python modern-quickstatements/build_browser_round.py "# round 14 (2026-10-09): 289913, DONE"
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "site"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_qs_home  # noqa: E402
from submit_full_batch import chunk_units  # noqa: E402
from direct_daily_edits import save_sequential_cursor  # noqa: E402

CHUNKS = os.path.join(HERE, "browser_chunks")
SENT = os.path.join(CHUNKS, "sequential_sent.json")
STATE = os.path.join(HERE, "sequential_misc.state")
REDIRECTS = os.path.join(CHUNKS, "redirects.json")


def advance_sequential_cursor():
    """Move the cursor past the lines the finished round sent. Never moves it backwards."""
    try:
        sent = int(json.load(io.open(SENT, encoding="utf-8"))["through"])
    except Exception:
        return None
    lines = build_qs_home.sequential_lines()
    sent = min(sent, len(lines))
    if sent > build_qs_home.sequential_cursor(lines):
        save_sequential_cursor(sent, path=STATE, lines=lines)
    return sent


def load_redirects():
    try:
        return json.load(io.open(REDIRECTS, encoding="utf-8"))
    except Exception:
        return {}


def record_redirects(pairs):
    """Merge {merged item: item it redirects to} into redirects.json, read off a finished
    batch's "No such entity" errors (Emma, 2026-10-09: "the merged ones we retarget")."""
    r = load_redirects()
    r.update(pairs)
    with io.open(REDIRECTS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(r, fh, indent=1, sort_keys=True)
    return r


def apply_redirects(units, redirects):
    """Statement lines (adds and removals) on a merged item move to the item it redirects to.
    Its label/description/alias/sitelink lines stay out: the merge carried the source's terms
    over, and a label line would overwrite the target's own label. Deleted items and rejected
    labels are NOT handled here; Emma wants those looked at, not skipped."""
    out = []
    for unit in units:
        kept = []
        for line in unit:
            parts = line.split("\t")
            neg = parts[0].startswith("-")
            subject = parts[0].lstrip("-")
            if subject in redirects:
                if len(parts) < 2 or not parts[1].startswith("P"):
                    continue
                parts[0] = ("-" if neg else "") + redirects[subject]
                line = "\t".join(parts)
            kept.append(line)
        if kept:
            out.append(kept)
    return out


def build_round(header):
    advance_sequential_cursor()
    chunks = chunk_units(apply_redirects(build_qs_home.build_units(), load_redirects()))
    total = sum(len(c) for c in chunks)
    if not total:
        return 0, 0
    for f in glob.glob(os.path.join(CHUNKS, "part_*.txt")):
        os.remove(f)
    for i, c in enumerate(chunks, 1):
        with io.open(os.path.join(CHUNKS, "part_%d.txt" % i), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(c) + "\n")
    with io.open(os.path.join(CHUNKS, "progress.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header.rstrip("\n") + "\n")
    with io.open(SENT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"through": len(build_qs_home.sequential_lines())}, fh)
    return total, len(chunks)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--record":
        print(len(record_redirects(json.load(io.open(sys.argv[2], encoding="utf-8")))), "redirects")
        sys.exit(0)
    total, parts = build_round(sys.argv[1] if len(sys.argv) > 1 else "# new round")
    print(total, parts)
