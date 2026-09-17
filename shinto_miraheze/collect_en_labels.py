#!/usr/bin/env python3
"""
collect_en_labels.py
====================
Collector for the ``en_label`` cloud-RAG queue (Stage 4 of
docs/english_label_pipeline.md, rebuilt as a remote-queue category -- see
build_en_label_queue.py for why Stage 4 went missing for 52 days).

Scans ``en_label/*.wiki`` for work-files whose ``<!-- ANSWER: ... -->`` marker the
cloud worker has filled, and:

  * ``LABEL: <english label>`` -> appends ``Qxxx|Len|"<label>"`` to
    modern-quickstatements/en_labels_sonnet.txt (an atomic file; the daily
    submitter drips it to Wikidata) and deletes the work-file.
  * ``SKIP: <reason>`` -> no QuickStatement; the verdict goes to
    en_label/_resolved.log and the work-file is deleted, so the builder does not
    re-queue the same unanswerable item forever.

Empty ANSWER -> untouched, still awaiting the worker. Mirrors
collect_label_typo_answers.py. Deterministic, idempotent, no network.

**The label is validated before it becomes a QuickStatement.** A QS line is
``Qxxx|Len|"..."``, so a quote or a newline in the payload does not produce a bad
label -- it produces a malformed COMMAND, and the submitter would carry it to
Wikidata as whatever it parsed to. A rejected answer is logged and its work-file
kept, never silently dropped and never half-written.

Usage: python collect_en_labels.py [--dry-run]
"""

import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(ROOT, "en_label")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "en_labels_sonnet.txt")
LOG = os.path.join(WORKDIR, "_resolved.log")

ANSWER_RE = re.compile(r"<!--\s*ANSWER:\s*(.*?)\s*-->", re.S)
QID_RE = re.compile(r"^(Q\d+)\.wiki$")

# A label we are willing to turn into a QuickStatement. Letters (incl. macrons,
# in case one slips through), digits, spaces, hyphen, apostrophe, period. No
# quote, no pipe, no newline -- those break the QS line itself.
_LABEL_OK = re.compile(r"^[A-Za-z0-9À-ɏ][A-Za-z0-9À-ɏ '.\-]*$")
_MAX_LABEL = 120


def parse_answer(text):
    """(kind, payload) from a work-file body, or None if ANSWER is empty."""
    m = ANSWER_RE.search(text)
    if not m or not m.group(1).strip():
        return None
    ans = m.group(1).strip()
    km = re.match(r"(LABEL|SKIP)\s*:\s*(.*)", ans, re.S)
    if not km:
        # A free-text answer is not a label. Treat it as a skip so a human can
        # read it, rather than guessing that the whole string was meant as one.
        return ("SKIP", ans)
    return (km.group(1), km.group(2).strip())


def validate(label):
    """None if the label is usable as a QS value, else the reason it is not."""
    if not label:
        return "empty label"
    if len(label) > _MAX_LABEL:
        return f"label too long ({len(label)} chars)"
    if not _LABEL_OK.match(label):
        return "label has characters that would break the QuickStatement line"
    return None


def collect(dry_run=False):
    if not os.path.isdir(WORKDIR):
        return {"pending": 0, "labels": 0, "skipped": 0, "rejected": 0}

    qs_lines, resolved, rejected, pending = [], [], [], 0
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
        if kind == "LABEL":
            why = validate(payload)
            if why:
                # Keep the work-file. A bad answer is a thing to look at, not a
                # thing to delete -- deleting it would also re-queue the item.
                rejected.append(f"{qid}\tREJECTED\t{why}\t{payload!r}")
                continue
            qs_lines.append(f'{qid}|Len|"{payload}"')
            resolved.append((path, f"{qid}\tLABEL\t{payload}"))
        else:
            resolved.append((path, f"{qid}\tSKIP\t{payload}"))

    if not dry_run:
        if qs_lines:
            with open(QS_OUT, "a", encoding="utf-8") as f:
                f.write("\n".join(qs_lines) + "\n")
        if resolved or rejected:
            with open(LOG, "a", encoding="utf-8") as f:
                for _, line in resolved:
                    f.write(line + "\n")
                for line in rejected:
                    f.write(line + "\n")
        for path, _ in resolved:
            os.remove(path)

    return {
        "pending": pending,
        "labels": len(qs_lines),
        "skipped": len(resolved) - len(qs_lines),
        "rejected": len(rejected),
    }


def main():
    # Inside main(): see build_en_label_queue.py.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description="Fold en_label answers into QS.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    r = collect(dry_run=args.dry_run)
    verb = "would append" if args.dry_run else "appended"
    print(f"en_label: pending={r['pending']} {verb} {r['labels']} QS lines, "
          f"skipped={r['skipped']}, rejected={r['rejected']}")
    if r["rejected"]:
        print("  rejected answers kept their work-file; see en_label/_resolved.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
