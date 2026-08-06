#!/usr/bin/env python3
"""
audit_label_overwrites.py
=========================
For every staged `Q…|L<lang>|"…"` line, report whether it ADDS a label, is a
NO-OP, or OVERWRITES an existing one — and show what it would overwrite.

WHY. The description pipeline was found on 2026-08-05 to be overwriting
hand-written Engishiki annotations with boilerplate, caught only because the
Wikidata freeze was still on. `L<lang>` has exactly the same shape as `Den`: it
SETS, it does not add. So the same question had to be asked of the ~12,150
staged label lines, and asked with data rather than reasoning.

The answer, that day: no label pipeline overwrites hand-written content. A
240-line stratified sample across the six bulk generators found 239 ADDs and one
NO-OP — they target items that have no label in the language. Every overwrite in
the corpus came from a file whose PURPOSE is correction, and each was already
evidenced:

  * label_typo_fixes.txt (79)      — researched per item against each shrine's
                                     own jawiki lead
  * french_elision_fixes.txt (25)  — the measured `de H` -> `d'H` decision,
                                     where the corpus itself ruled 3,645 to 25
  * category_label_fixes.txt (42)  — adds the `Category:` prefix to items that
                                     really are P31=Q4167836 Wikimedia
                                     categories, whose ja labels already carry
                                     it and whose sitelinks are jawiki
                                     `Category:` pages
  * miscellaneous_edits.txt (1)    — REMOVES a `Category:` prefix from
                                     Q138565446, which is a shrine: its jawiki
                                     sitelink is a mainspace article and the
                                     prefix was copied in from its *Commons*
                                     category sitelink

Those last two look contradictory and are not. That is the point of running the
audit instead of reasoning about the filenames.

This cannot be a CI test — it needs live Wikidata — so it is a script to run
before a drip resumes, or whenever a new label generator is added.

Usage:
    python audit_label_overwrites.py                 # every staged label line
    python audit_label_overwrites.py --sample 40     # N lines per file
    python audit_label_overwrites.py --file en_labels.txt
"""
import argparse
import collections
import io
import os
import random
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("ShintoWikiLabels/1.0 "
      "(https://github.com/EmmaLeonhart/shintowiki-scripts; emma@topazcomputing.com)")
API = "https://www.wikidata.org/w/api.php"

# `-Qxxx|Len|…` is a label REMOVAL; the dash is the command. Matched so a
# removal is never silently read as an add.
LINE = re.compile(r'^(-?)(Q\d+)\|L([a-z-]+)\|"(.*)"$')


def label_lines(text):
    """[(qid, lang, value, is_removal)] — pure, so the parsing is testable."""
    out = []
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if m:
            out.append((m.group(2), m.group(3), m.group(4), m.group(1) == "-"))
    return out


def classify(current, staged, is_removal):
    """What this line would do to the live label."""
    if is_removal:
        return "REMOVE" if current is not None else "NO-OP"
    if current is None:
        return "ADD"
    return "NO-OP" if current == staged else "OVERWRITE"


def fetch_labels(qids, langs):
    out = {}
    qids = sorted(set(qids))
    for i in range(0, len(qids), 50):
        r = requests.get(API, params={
            "action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
            "props": "labels", "languages": "|".join(sorted(langs)),
            "format": "json"}, headers={"User-Agent": UA}, timeout=90)
        if r.status_code == 429:
            raise SystemExit("429 from Wikidata — bailing (CLAUDE.md 429 policy).")
        r.raise_for_status()
        out.update(r.json()["entities"])
        time.sleep(0.3)
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0,
                    help="audit only N lines per file (0 = all)")
    ap.add_argument("--file", help="audit a single .txt")
    ap.add_argument("--seed", type=int, default=20260805)
    args = ap.parse_args()
    random.seed(args.seed)

    names = ([args.file] if args.file
             else sorted(f for f in os.listdir(HERE) if f.endswith(".txt")))
    rows = []
    for name in names:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            raise SystemExit(f"no such file: {name}")
        found = label_lines(open(path, encoding="utf-8").read())
        if args.sample and len(found) > args.sample:
            found = random.sample(found, args.sample)
        rows += [(name,) + f for f in found]

    if not rows:
        print("no staged label lines")
        return
    print(f"auditing {len(rows)} label line(s)"
          f"{' (sampled)' if args.sample else ''}\n")

    ents = fetch_labels([r[1] for r in rows], {r[2] for r in rows})
    stat = collections.Counter()
    detail = collections.defaultdict(list)
    for name, qid, lang, staged, rm in rows:
        cur = ents.get(qid, {}).get("labels", {}).get(lang, {}).get("value")
        k = classify(cur, staged, rm)
        stat[(name, k)] += 1
        if k in ("OVERWRITE", "REMOVE"):
            detail[name].append(f"{qid} [{lang}] {cur!r} -> {staged!r}")

    total = collections.Counter()
    for name in names:
        parts = [f"{stat[(name, k)]} {k}"
                 for k in ("ADD", "NO-OP", "OVERWRITE", "REMOVE") if stat[(name, k)]]
        if not parts:
            continue
        print(f"{name}: {', '.join(parts)}")
        for d in detail[name][:8]:
            print(f"    {d}")
        if len(detail[name]) > 8:
            print(f"    … and {len(detail[name]) - 8} more")
        for k in ("ADD", "NO-OP", "OVERWRITE", "REMOVE"):
            total[k] += stat[(name, k)]
    print("\nTOTAL: " + ", ".join(f"{n} {k}" for k, n in total.most_common()))
    if total["OVERWRITE"]:
        print("\nAn OVERWRITE is not automatically wrong — the correction files exist\n"
              "to make them. It is wrong when the value being replaced was written by\n"
              "hand. Read the pairs above before letting a drip resume.")


if __name__ == "__main__":
    main()
