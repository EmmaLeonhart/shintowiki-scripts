#!/usr/bin/env python3
"""Emit a targeted QuickStatements file for the recreation candidates that never got
created on Wikidata (no exact-ja item exists for them), so Emma can run JUST those
without re-running the full RUNNABLE batch (which would duplicate the ~159 already
created — CREATE always mints a NEW item).

Why these four failed / were skipped (verified live 2026-07-06):
  * 大伝馬町天王祭 (Q135504314): its ``Sjawiki`` pointed at ``祇園祭#…`` — a section anchor
    (invalid as a sitelink) whose base page 祇園祭 is already Q979873 → sitelink conflict.
  * 十二天王 (Q135504457): its ``Sjawiki`` 御霊神社 (藤沢市宮前) is already Q20044399 →
    sitelink conflict. (Host-page sitelinks are wrong for a sub-topic ill-target anyway.)
  * 赤城神社 (前橋市荒口町) (Q135505918) and 岩衝別命 (Q135579300): no sitelink; simply not run.

Fix: drop every ``Sjawiki`` line (the host-page/section sitelinks that caused the
conflicts and don't belong on sub-topic items), keep labels + description + P31 (+ P17).
The result creates all four cleanly. Recreation stays human-gated — Emma runs the output
through QuickStatements; this script only writes the .txt.

``五社権現`` (Q135579265) is deliberately EXCLUDED: it WAS created (as Q140446115) and then
merged into Q140446113 — its ill already points there. It is resolved, not uncreated.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNABLE = os.path.join(HERE, "recreation_quickstatements_RUNNABLE.txt")
OUT = os.path.join(HERE, "recreation_create_missing.txt")

# deleted-QID stems whose items have no exact-ja Wikidata item (verified live) and are
# NOT merge artifacts — i.e. the recreation blocks that still need to be run.
MISSING = {
    "大伝馬町天王祭",
    "十二天王",
    "赤城神社 (前橋市荒口町)",
    "岩衝別命",
}


def blocks(text):
    """Yield each ``CREATE\\n…`` block (list of its non-empty lines)."""
    cur = []
    for line in text.splitlines():
        if line.strip() == "CREATE":
            if cur:
                yield cur
            cur = ["CREATE"]
        elif line.strip():
            cur.append(line)
    if cur:
        yield cur


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    text = open(RUNNABLE, encoding="utf-8").read()
    out_blocks = []
    for blk in blocks(text):
        ja = next((l.split("\t")[2].strip('"') for l in blk
                   if "\tLja\t" in l), None)
        if ja not in MISSING:
            continue
        # drop the conflicting host-page/section sitelink
        cleaned = [l for l in blk if "\tSjawiki\t" not in l]
        out_blocks.append(cleaned)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        for blk in out_blocks:
            fh.write("\n".join(blk) + "\n\n")

    print(f"Wrote {len(out_blocks)} CREATE blocks → {os.path.relpath(OUT, HERE)}")
    if len(out_blocks) != len(MISSING):
        found = {next((l.split(chr(9))[2].strip('\"') for l in b if chr(9)+'Lja'+chr(9) in l), '?') for b in out_blocks}
        print(f"  WARNING: expected {len(MISSING)}, found {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
