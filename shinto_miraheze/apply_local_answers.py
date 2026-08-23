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

⚠ THE QUEUES ARE NOT ALL SHAPED THE SAME, and assuming they were made three of the
six advertised options dead (found 2026-08-23, by running one).

    queue                   key            file                       marker
    name_in_kana            Qxxx           <key>.wiki                 ANSWER:
    beppyo_p612             Qxxx           <key>.wiki                 ANSWER:
    label_typo              Qxxx           <key>.wiki                 ANSWER:
    ronsha_ranking          Qxxx           <key>.wiki                 ANSWER:
    description_enrichment  member Qxxx    the file whose ANSWERS      ANSWERS: block,
                                           block holds that QID        one `Qxxx: ` line
    category_translation    Category:...   <title, ':'→%3A>.wiki      TRANSLATED:

`description_enrichment` work-files are named after the GROUP's first member, and
the answerable members are the OTHER QIDs inside the block — so `<key>.wiki` finds
the wrong file, or none. `category_translation` is not QID-keyed at all.

That last one failed in the worst available way: the old loader dropped any row
whose first column was not `^Q\\d+$` **before** any counter, so a category batch
printed `would write 0 answer(s) (0 gone, 0 answered, 0 with no marker)` — four
zeros, which is also exactly what a correct run on an empty batch prints. Rows are
now rejected loudly, with the line number and the reason.

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

# Work-queue name -> (directory, marker name, key kind). The directory mirrors the
# WORKDIR constant of the matching collect_*.py and the marker mirrors its own
# ANSWER_RE; a queue absent here cannot be answered, which is deliberate.
#
# key kinds:
#   "qid"      the key IS the filename stem
#   "member"   the key is a member QID; the file is whichever one holds it
#   "category" the key is a full `Category:` title, encoded into the filename by
#              the same rule build_category_translation_queue._safe_filename uses
QUEUES = {
    "name_in_kana": ("name_in_kana", "ANSWER", "qid"),
    "beppyo_p612": ("beppyo_p612", "ANSWER", "qid"),
    "description_enrichment": ("description_enrichment_en", "ANSWERS", "member"),
    "label_typo": ("label_typo_review", "ANSWER", "qid"),
    "ronsha_ranking": ("ronsha_ranking_review", "ANSWER", "qid"),
    "category_translation": ("category_translation", "TRANSLATED", "category"),
}

QID_RE = re.compile(r"^Q\d+$")


def marker_re(name):
    """Scalar marker, e.g. `<!-- ANSWER: … -->` or `<!-- TRANSLATED: … -->`.

    Anchored with a negative lookahead on a word character so `ANSWER` does not
    also match `ANSWERS:` — the difference between the two is the whole reason
    description_enrichment silently answered nothing.
    """
    return re.compile(r"(<!--\s*" + name + r":(?!\w)\s*)(.*?)(\s*-->)", re.S)


def fill(head, answer, tail):
    """The replacement text for a matched marker, with spacing normalised.

    Splicing straight around the regex groups emitted `<!-- ANSWER:  value-->`,
    because `\\s*` after the colon is greedy and `(\\s*-->)` then matched no space.
    Every collector strips around the value so it parsed — but a hand-answered file
    did not look like a routine-answered one, which matters when the next person
    is eyeballing a directory to see what has been touched.
    """
    return head.rstrip() + " " + answer + (" " + tail.lstrip() if tail else "")


def block_line_re(qid):
    """One `Qxxx: <answer>` line inside a description_enrichment ANSWERS block."""
    return re.compile(r"(^" + qid + r":[ \t]*)(.*)$", re.M)


def safe_filename(title):
    """Mirror build_category_translation_queue._safe_filename exactly."""
    return title.replace(":", "%3A").replace("/", "%2F") + ".wiki"


def locate(workdir, key, kind, scalar):
    """The work-file this key belongs to, or None if it is already gone.

    For "member" the filename is NOT the key: a description_enrichment work-file
    is named after the group's first member and answers the others, so the file
    has to be found by looking inside each ANSWERS block.
    """
    if kind == "category":
        path = os.path.join(workdir, safe_filename(key))
        return path if os.path.exists(path) else None
    if kind == "qid":
        path = os.path.join(workdir, f"{key}.wiki")
        return path if os.path.exists(path) else None
    line = block_line_re(key)
    for name in sorted(os.listdir(workdir)):
        if not name.endswith(".wiki"):
            continue
        path = os.path.join(workdir, name)
        body = open(path, encoding="utf-8").read()
        block = scalar.search(body)
        if block and line.search(body, block.start(), block.end()):
            return path
    return None


def load_answers(path, kind):
    """Read the TSV. A row that cannot be used is REPORTED, never dropped quietly.

    The old version filtered on `^Q\\d+$` with no counter, so a whole category
    batch vanished into a report of four zeros.
    """
    out, bad = [], []
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                bad.append((n, line, "not two tab-separated columns"))
                continue
            key = parts[0].strip()
            if kind in ("qid", "member") and not QID_RE.match(key):
                bad.append((n, line, "key is not a QID"))
                continue
            if kind == "category" and not key.startswith("Category:"):
                bad.append((n, line, "key is not a 'Category:…' title"))
                continue
            out.append((key, parts[1].strip()))
    return out, bad


def main():
    # Inside main(), never at module scope: importing this module used to replace
    # the CALLER's stdout, which breaks pytest's capture outright. Third instance
    # of the same bug in this repo (generate_soja_only.py,
    # build_label_typo_review_queue.py were the first two).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True, choices=sorted(QUEUES))
    ap.add_argument("--answers", required=True,
                    help="TSV path, absolute or relative to shinto_miraheze/")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an ANSWER that is already filled")
    args = ap.parse_args()

    dirname, marker, kind = QUEUES[args.queue]
    workdir = os.path.join(ROOT, dirname)
    answers, bad = load_answers(args.answers if os.path.isabs(args.answers)
                                else os.path.join(SCRIPT_DIR, args.answers), kind)
    for n, line, why in bad:
        print(f"REJECT line {n}: {why} — {line[:70]!r}")

    scalar = marker_re(marker)
    written = missing = occupied = unmarked = 0
    for key, answer in answers:
        path = locate(workdir, key, kind, scalar)
        if path is None:
            # Usually the right outcome, not an error: the collector deletes a
            # work-file once it is answered, so a missing one is already done.
            missing += 1
            continue
        body = open(path, encoding="utf-8").read()

        if kind == "member":
            block = scalar.search(body)
            m = block_line_re(key).search(body, block.start(), block.end())
            tail = ""          # the line ends at the newline; nothing to restore
            what = f"'{key}:' line in the {marker} block"
        else:
            m = scalar.search(body)
            tail = m.group(3) if m else ""
            what = f"{marker} marker"
        if m is None:
            print(f"{key}: no {what} — skipped")
            unmarked += 1
            continue

        head, existing = m.group(1), m.group(2)
        if existing.strip() and not args.force:
            print(f"{key}: already answered ({existing.strip()[:40]}) — skipped")
            occupied += 1
            continue
        filled = fill(head, answer, tail)
        if args.apply:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body[:m.start()] + filled + body[m.end():])
        written += 1

    verb = "wrote" if args.apply else "would write"
    # For "member" a miss is not necessarily a collected file: the QID may simply
    # not be an answerable member of any group (a protected one is left out of the
    # block on purpose). Do not report it as though it had been done.
    gone = ("no work-file holds this key (collected, or not an answerable member)"
            if kind == "member" else "work-file(s) already gone")
    print(f"{verb} {written} answer(s) into {dirname}/ "
          f"({missing} {gone}, {occupied} already answered, "
          f"{unmarked} with no marker, {len(bad)} row(s) rejected)")
    if not args.apply:
        print("dry run; pass --apply")


if __name__ == "__main__":
    main()
