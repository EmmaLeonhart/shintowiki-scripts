#!/usr/bin/env python3
"""
apply_local_answers.py
======================
Fill the `<!-- ANSWER: ... -->` markers of a cloud work-queue from a local TSV,
so a batch can be answered here instead of waiting on the remote routine.

The routine is one path to these queues, not the only one — it answers a handful
of items per run across thousands of entries, so working a queue locally in
batches is usually faster (queue.md A0). The collectors do not care who filled
the marker, so nothing downstream changes: `collect_*.py` still applies its own
gates, still writes the QuickStatements, still deletes the file.

TSV format, two columns, `#` comments and a header line both ignored:

    Q12345 <tab> KANA: いせじんぐう

The answer text is written VERBATIM. Deciding whether it is acceptable is the
collector's job, not this script's — duplicating the gate here would mean two
places to keep in step, and the collector is the one that runs in CI.

REFUSES TO OVERWRITE a marker that is already filled: a non-empty ANSWER is
either the routine's work or an earlier local pass, and silently replacing it
would lose whichever was right. Pass --force only when you mean to.

Usage:
    python shinto_miraheze/apply_local_answers.py --queue name_in_kana \\
        --answers local_answers/name_in_kana_2026-08-04.tsv [--apply]

Default is a dry run.
"""
import argparse
import io
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Work-queue name -> the directory its work-files live in. These mirror the
# WORKDIR constant of the matching collect_*.py; a queue absent here cannot be
# answered, which is deliberate.
QUEUES = {
    "name_in_kana": "name_in_kana",
    "beppyo_p612": "beppyo_p612",
    "description_enrichment": "description_enrichment_en",
    "label_typo": "label_typo_review",
    "ronsha_ranking": "ronsha_ranking_review",
    "category_translation": "category_translation",
}

ANSWER_RE = re.compile(r"(<!--\s*ANSWER:\s*)(.*?)(\s*-->)", re.S)


def load_answers(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2 or not re.match(r"^Q\d+$", parts[0].strip()):
                continue
            out.append((parts[0].strip(), parts[1].strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True, choices=sorted(QUEUES))
    ap.add_argument("--answers", required=True,
                    help="TSV path, absolute or relative to shinto_miraheze/")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an ANSWER that is already filled")
    args = ap.parse_args()

    workdir = os.path.join(ROOT, QUEUES[args.queue])
    answers = load_answers(args.answers if os.path.isabs(args.answers)
                           else os.path.join(SCRIPT_DIR, args.answers))

    written = missing = occupied = unmarked = 0
    for qid, answer in answers:
        path = os.path.join(workdir, f"{qid}.wiki")
        if not os.path.exists(path):
            # Usually the right outcome, not an error: the collector deletes a
            # work-file once it is answered, so a missing one is already done.
            missing += 1
            continue
        body = open(path, encoding="utf-8").read()
        m = ANSWER_RE.search(body)
        if not m:
            print(f"{qid}: no ANSWER marker — skipped")
            unmarked += 1
            continue
        if m.group(2).strip() and not args.force:
            print(f"{qid}: already answered ({m.group(2).strip()[:40]}) — skipped")
            occupied += 1
            continue
        if args.apply:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body[:m.start()] + m.group(1) + answer + m.group(3)
                         + body[m.end():])
        written += 1

    verb = "wrote" if args.apply else "would write"
    print(f"{verb} {written} answer(s) into {QUEUES[args.queue]}/ "
          f"({missing} work-file(s) already gone, {occupied} already answered, "
          f"{unmarked} with no marker)")
    if not args.apply:
        print("dry run; pass --apply")


if __name__ == "__main__":
    main()
