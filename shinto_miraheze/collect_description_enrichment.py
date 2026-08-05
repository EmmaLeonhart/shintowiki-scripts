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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_description_enrichment_queue import needs_a_description  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(ROOT, "description_enrichment_en")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "description_enrichment_en.txt")
RESOLVED = os.path.join(WORKDIR, "_resolved.log")

BLOCK_RE = re.compile(r"<!--\s*ANSWERS:\s*\n(.*?)-->", re.S)
# [ \t]* NOT \s* — \s matches newlines even without DOTALL, which made an
# empty answer swallow the next line's QID as its "answer" (caught 2026-07-08).
LINE_RE = re.compile(r"^(Q\d+):[ \t]*(.*)$", re.M)

# Second gate, independent of the builder's. `Den` OVERWRITES, and 15 of the
# first 22 staged lines would have replaced a hand-written Engishiki annotation
# ('Ronsha 3 of Yaahino Shrine') with location boilerplate. The builder now
# refuses to ask for those, but work-files already on disk still carry the old
# ask, and an answer filled by the cloud routine arrives here regardless.
#
# No network needed: the builder records each member's existing description in
# the Members section, so the work-file itself says what would be destroyed.
MEMBER_DESC_RE = re.compile(
    r"^\* \[\[d:(Q\d+)\]\].*?EXISTING en desc: '(.*?)'", re.M)


def protected_members(text):
    """{qid: existing description} for members this pipeline must not overwrite."""
    return {q: d for q, d in MEMBER_DESC_RE.findall(text)
            if not needs_a_description(d)}


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
    pending = resolved = rejected = blocked = 0
    qs = []
    for fn in sorted(os.listdir(WORKDIR)):
        if not fn.endswith(".wiki"):
            continue
        path = os.path.join(WORKDIR, fn)
        filled = parse(open(path, encoding="utf-8").read())
        if not filled:
            pending += 1
            continue
        body = open(path, encoding="utf-8").read()
        protected = protected_members(body)
        clobber = {q: protected[q] for q in filled if q in protected}
        if clobber:
            for q, existing in sorted(clobber.items()):
                print(f"REFUSE {fn} {q}: would overwrite a hand-written "
                      f"description {existing!r} with {filled[q]!r}")
                blocked += 1
            filled = {q: a for q, a in filled.items() if q not in clobber}
            if not filled:
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
          f"blocked-would-overwrite={blocked} "
          f"qs-lines={len(qs)}{' [DRY]' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
