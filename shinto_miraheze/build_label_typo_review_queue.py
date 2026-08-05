#!/usr/bin/env python3
"""
build_label_typo_review_queue.py
================================
Queue #8 typo review -> cloud RAG. Parses the committed audit table
(docs/kana_label_mismatch_audit_2026-07.md — 161 shrines whose EN label letters
diverge from their romanized P1814 kana) and writes one work-file per candidate
into label_typo_review/, for the claude.ai remote routine (remote_queue.py emits
them). The worker researches WHICH side is wrong (label typo? historical-kana
P1814? legit place-prefix?) and fills the ANSWER marker; a collector then folds
answers into QS lines (follow-up). Idempotent: skips existing work-files.

Usage: python build_label_typo_review_queue.py
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "docs", "kana_label_mismatch_audit_2026-07.md")
OUTDIR = os.path.join(ROOT, "label_typo_review")

TASK = (
    "<!-- TASK: this shrine's English label letters diverge from its romanized kana "
    "(P1814). Research (jawiki article, official site, romanization rules) and decide "
    "which side is wrong. Fill ANSWER with exactly one of:\n"
    "  LABEL_TYPO: <corrected English label>   (the label is misspelled)\n"
    "  KANA_ISSUE: <note, e.g. historical kana ちりふ=Chiryū>  (label fine, kana archaic/wrong)\n"
    "  PREFIX_OK: <note>                        (label carries a legit place/disambiguator prefix)\n"
    "  OTHER: <explanation>\n"
    "When ANSWER is filled this file is done. -->"
)


RESOLVED_LOG = os.path.join(OUTDIR, "_resolved.log")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "label_typo_fixes.txt")


def already_handled():
    """QIDs already answered or already staged — do NOT queue them again.

    "Skip if the work-file exists" is not enough, and this is the third builder
    to be bitten by it: the collector DELETES the work-file when it answers, so
    absence means "done" just as often as it means "never queued". The staged
    .txt cannot be consulted alone either, because a decision of "nothing is
    wrong here" correctly produces no QS line at all — those live only in
    _resolved.log. Both are read.
    """
    done = set()
    for path, pattern in ((RESOLVED_LOG, r"^(Q\d+)\b"), (QS_OUT, r"^-?(Q\d+)\|")):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            m = re.match(pattern, line)
            if m:
                done.add(m.group(1))
    return done


def main():
    # Inside main(), not at module scope: rebinding on import replaces the
    # caller's stdout, which breaks pytest's capture and any importer. Same fix
    # already applied to generate_soja_only.py. The UTF-8 wrapper is still
    # required — this is a CLI script and Windows defaults to cp1252.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = []
    for line in open(AUDIT, encoding="utf-8"):
        m = re.match(r"\| (Q\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|\s*$", line)
        if m:
            rows.append(m.groups())
    os.makedirs(OUTDIR, exist_ok=True)
    handled = already_handled()
    new = 0
    for qid, ja, kana, en, roma in rows:
        path = os.path.join(OUTDIR, f"{qid}.wiki")
        if os.path.exists(path) or qid in handled:
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
                    f"<!-- JA: {ja} | KANA: {kana} | EN_LABEL: {en} | KANA_ROMANIZED: {roma} -->\n"
                    f"<!-- ANSWER: -->\n{TASK}\n")
        new += 1
    print(f"{len(rows)} audit rows -> {new} new work-files in label_typo_review/ "
          f"({len(rows) - new} already existed)")


if __name__ == "__main__":
    main()
