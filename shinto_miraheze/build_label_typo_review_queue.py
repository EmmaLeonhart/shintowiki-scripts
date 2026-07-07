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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
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


def main():
    rows = []
    for line in open(AUDIT, encoding="utf-8"):
        m = re.match(r"\| (Q\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|\s*$", line)
        if m:
            rows.append(m.groups())
    os.makedirs(OUTDIR, exist_ok=True)
    new = 0
    for qid, ja, kana, en, roma in rows:
        path = os.path.join(OUTDIR, f"{qid}.wiki")
        if os.path.exists(path):
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
