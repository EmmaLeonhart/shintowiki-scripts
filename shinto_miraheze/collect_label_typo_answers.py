#!/usr/bin/env python3
"""
collect_label_typo_answers.py
=============================
Collector for the label_typo_review cloud-RAG queue (queue #8). Scans
label_typo_review/*.wiki for work-files whose `<!-- ANSWER: ... -->` marker the
cloud worker has filled, and:

  * `LABEL_TYPO: <corrected label>` -> appends `Qxxx|Len|"<label>"` to
    modern-quickstatements/label_typo_fixes.txt (atomic file; the daily
    direct_daily_edits pipeline applies it) and deletes the work-file.
  * `KANA_ISSUE:` / `PREFIX_OK:` / `OTHER:` -> no Wikidata edit (the label is
    fine or the fix isn't label-side); the verdict is appended to
    label_typo_review/_resolved.log and the work-file is deleted.

Empty ANSWER -> untouched (still awaiting the worker). Mirrors
collect_category_translations.py. Deterministic, idempotent, no network.

Usage: python collect_label_typo_answers.py [--dry-run]
"""

import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(ROOT, "label_typo_review")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "label_typo_fixes.txt")
LOG = os.path.join(WORKDIR, "_resolved.log")

ANSWER_RE = re.compile(r"<!--\s*ANSWER:\s*(.*?)\s*-->", re.S)
QID_RE = re.compile(r"^(Q\d+)\.wiki$")


def parse_answer(text):
    """(kind, payload) from a work-file body, or None if ANSWER is empty."""
    m = ANSWER_RE.search(text)
    if not m or not m.group(1).strip():
        return None
    ans = m.group(1).strip()
    km = re.match(r"(LABEL_TYPO|KANA_ISSUE|PREFIX_OK|OTHER)\s*:\s*(.*)", ans, re.S)
    if not km:
        return ("OTHER", ans)  # free-text answer -> reviewed, no auto-QS
    return (km.group(1), km.group(2).strip())


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(WORKDIR):
        print("no label_typo_review/ dir; nothing to collect")
        return
    qs_lines, resolved, pending = [], [], 0
    for name in sorted(os.listdir(WORKDIR)):
        qm = QID_RE.match(name)
        if not qm:
            continue
        qid = qm.group(1)
        path = os.path.join(WORKDIR, name)
        parsed = parse_answer(open(path, encoding="utf-8").read())
        if parsed is None:
            pending += 1
            continue
        kind, payload = parsed
        if kind == "LABEL_TYPO" and payload and '"' not in payload:
            qs_lines.append(f'{qid}|Len|"{payload}"')
        resolved.append((path, f"{qid}\t{kind}\t{payload}"))

    print(f"pending={pending} resolved={len(resolved)} label-fixes={len(qs_lines)}")
    if args.dry_run:
        for _, r in resolved[:10]:
            print("  ", r)
        return
    if qs_lines:
        with open(QS_OUT, "a", encoding="utf-8") as f:
            f.write("\n".join(qs_lines) + "\n")
    if resolved:
        with open(LOG, "a", encoding="utf-8") as f:
            for _, r in resolved:
                f.write(r + "\n")
        for path, _ in resolved:
            os.remove(path)
    print(f"appended {len(qs_lines)} QS lines; removed {len(resolved)} work-files")


if __name__ == "__main__":
    main()
