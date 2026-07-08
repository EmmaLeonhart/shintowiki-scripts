#!/usr/bin/env python3
"""
collect_description_enrichment.py
==================================
Collector for the description_enrichment_en cloud-RAG queue (stage 1 of
`docs/description_enrichment_pipeline.md`). Scans work-files for filled
ANSWERS blocks:

    <!-- ANSWERS:
    Q123: Shinto shrine in Maebashi, Gunma Prefecture, Japan
    Q456: Shinto shrine dedicated to Akagi in Shibukawa, Gunma, Japan
    -->

The uniqueness rule applies at collection: only answers that are unique
WITHIN their group are emitted (duplicates within a group are all rejected
and reported — the file stays for another pass). Empty answer lines are
allowed (the worker found nothing distinguishing) — a file is DONE when at
least one answer is filled and no duplicates exist among the filled ones;
emitted members get `Q|Den|"…"` lines, unanswered members are logged.

Output: modern-quickstatements/description_enrichment_en.txt (ATOMIC).
Processed files are deleted; ids logged to _resolved.log.

Usage: python collect_description_enrichment.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(ROOT, "description_enrichment_en")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "description_enrichment_en.txt")
RESOLVED = os.path.join(WORKDIR, "_resolved.log")

BLOCK_RE = re.compile(r"<!--\s*ANSWERS:\s*\n(.*?)-->", re.S)
# [ \t]* NOT \s* — \s matches newlines even without DOTALL, which made an
# empty answer swallow the next line's QID as its "answer" (caught 2026-07-08).
LINE_RE = re.compile(r"^(Q\d+):[ \t]*(.*)$", re.M)


def parse(text):
    """{qid: answer} for filled lines, or None if the block is untouched."""
    m = BLOCK_RE.search(text)
    if not m:
        return None
    answers = {q: a.strip() for q, a in LINE_RE.findall(m.group(1))}
    filled = {q: a for q, a in answers.items() if a}
    return filled if filled else None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(WORKDIR):
        print("no description_enrichment_en/ dir; nothing to collect")
        return
    pending = resolved = rejected = 0
    qs = []
    for fn in sorted(os.listdir(WORKDIR)):
        if not fn.endswith(".wiki"):
            continue
        path = os.path.join(WORKDIR, fn)
        filled = parse(open(path, encoding="utf-8").read())
        if not filled:
            pending += 1
            continue
        dupes = {a for a, n in Counter(filled.values()).items() if n > 1}
        if dupes:
            rejected += 1
            print(f"REJECT {fn}: duplicate answers within group: {sorted(dupes)[:2]}")
            continue
        for q, a in sorted(filled.items()):
            esc = a.replace('"', '""')
            qs.append(f'{q}|Den|"{esc}"')
        resolved += 1
        if not args.dry_run:
            with open(RESOLVED, "a", encoding="utf-8") as f:
                f.write(f"{fn} {len(filled)} answers\n")
            os.remove(path)
    if qs and not args.dry_run:
        with open(QS_OUT, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(qs) + "\n")
    print(f"pending={pending} resolved={resolved} rejected-dup={rejected} "
          f"qs-lines={len(qs)}{' [DRY]' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
