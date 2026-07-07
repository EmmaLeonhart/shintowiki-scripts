#!/usr/bin/env python3
"""
collect_category_translations.py
================================
The back half of queue item 5. The cloud remote routine fills the
``<!-- TRANSLATED: Category:... -->`` marker in each ``category_translation/
*.wiki`` work-file (written by ``build_category_translation_queue.py``). This
script folds every FINISHED file into ``category_moves.csv`` — the same 2-column
``source,destination`` CSV the monthly ``move_categories`` step consumes — and
deletes the finished file (its job is done; the move happens downstream).

Rules (never machine-guess — that's the whole point of routing to RAG):
  * A file is DONE when its TRANSLATED marker holds a ``Category:...`` value.
    → append ``SOURCE,TRANSLATED`` to the CSV, delete the file.
  * A file marked ``<!-- SKIP: reason -->`` (genuinely untranslatable) → leave it
    in place for human review; do NOT write a row.
  * A file with an empty TRANSLATED marker and no SKIP → not done yet; leave it.
  * Never write a row whose destination isn't a ``Category:`` title, or equals the
    source — that would be a malformed/no-op move.

Idempotent + append-only: existing CSV rows are preserved and a source already in
the CSV is never duplicated. ``--apply`` writes; default dry-run reports.
"""
import argparse
import csv
import glob
import io
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
WORK_DIR = os.path.join(REPO_ROOT, "category_translation")
CSV_PATH = os.path.join(SCRIPT_DIR, "category_moves.csv")

_SOURCE_RE = re.compile(r"<!--\s*SOURCE:\s*(Category:[^>]*?)\s*-->")
_TRANSLATED_RE = re.compile(r"<!--\s*TRANSLATED:\s*(.*?)\s*-->")
# Anchored to line start: the TASK instruction in every work-file quotes a
# literal '<!-- SKIP: <reason> -->' example MID-LINE; an unanchored match read
# that example as a real marker and classified all 378 work-files as skipped,
# masking finished answers (2026-07-07). A real SKIP is a line of its own.
_SKIP_RE = re.compile(r"^\s*<!--\s*SKIP:\s*(.*?)\s*-->", re.M)


def _existing_sources() -> set:
    out = set()
    if not os.path.exists(CSV_PATH):
        return out
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row:
                out.add(row[0].strip())
    return out


def parse_file(text: str):
    """Return (source, translated, skip) — any may be None/'' if absent."""
    s = _SOURCE_RE.search(text)
    t = _TRANSLATED_RE.search(text)
    k = _SKIP_RE.search(text)
    return (s.group(1).strip() if s else None,
            t.group(1).strip() if t else "",
            k.group(1).strip() if k else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Append rows to category_moves.csv + delete finished files.")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    existing = _existing_sources()
    rows = []          # (source, dest, path)
    pending = skipped = malformed = 0
    for path in sorted(glob.glob(os.path.join(WORK_DIR, "*.wiki"))):
        source, translated, skip = parse_file(open(path, encoding="utf-8").read())
        if not source:
            malformed += 1
            continue
        if skip:
            skipped += 1
            continue
        if not translated:
            pending += 1
            continue
        # Validate the answer before trusting it.
        if not translated.startswith("Category:") or translated == source:
            print(f"MALFORMED answer in {os.path.basename(path)}: {translated!r}")
            malformed += 1
            continue
        if source in existing:
            # already in the CSV from a prior run — just clear the finished file
            rows.append((source, translated, path))
            continue
        rows.append((source, translated, path))
        existing.add(source)

    print(f"Finished (→ CSV): {len(rows)} | pending: {pending} | "
          f"skipped (human): {skipped} | malformed: {malformed}")
    for s, d, _ in rows[:12]:
        print(f"  {s}  ->  {d}")

    if not args.apply:
        print("\n[DRY] pass --apply to append rows + delete finished files")
        return

    if rows:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for s, d, _ in rows:
                w.writerow([s, d])
        for _, _, path in rows:
            os.remove(path)
        print(f"Appended {len(rows)} rows to {CSV_PATH}; deleted {len(rows)} finished files.")


if __name__ == "__main__":
    main()
