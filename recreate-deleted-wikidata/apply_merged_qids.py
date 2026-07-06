#!/usr/bin/env python3
"""Apply Wikidata merges to the local repo: replace each merged QID with its
surviving QID everywhere the recreated items are referenced — the git_synced/ page
ills, the modern-quickstatements/ relations queue, and the item JSONs.

Emma merges duplicate items she finds among the recreated set (first: Q140446120 →
Q11587884). List each in ``merged_qids.txt`` as ``<merged>\\t<surviving>``; this
rewrites the ill targets + queued relation statements + recorded recreated_qid so
everything points at the surviving item. Whole-QID-token replacement (Q1 never
matches inside Q10). Dry-run by default; ``--apply`` writes.
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MERGES = os.path.join(HERE, "merged_qids.txt")
_QID = re.compile(r"Q\d+")


def load_merges(path=MERGES):
    """{merged_qid: surviving_qid} from merged_qids.txt (skips #/blank lines). Pure."""
    out = {}
    if not os.path.exists(path):
        return out
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        if len(parts) >= 2 and re.fullmatch(r"Q\d+", parts[0]) and re.fullmatch(r"Q\d+", parts[1]):
            out[parts[0]] = parts[1]
    return out


def apply_merges(text, merges):
    """Replace whole-QID tokens per the merges map; unmapped QIDs untouched. Pure."""
    return _QID.sub(lambda m: merges.get(m.group(0), m.group(0)), text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    merges = load_merges()
    if not merges:
        print("No merges in merged_qids.txt — nothing to do.")
        return 0
    print(f"Merges: {merges}")

    targets = (glob.glob(os.path.join(REPO, "git_synced", "*.wiki"))
               + [os.path.join(REPO, "modern-quickstatements", "recreation_relations.txt")]
               + glob.glob(os.path.join(HERE, "items", "Q*.json")))
    changed = 0
    for path in targets:
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        new = apply_merges(text, merges)
        if new != text:
            changed += 1
            print(f"  {'wrote' if args.apply else 'would change'}: {os.path.relpath(path, REPO)}")
            if args.apply:
                open(path, "w", encoding="utf-8", newline="\n").write(new)
    print(f"\n{'APPLIED' if args.apply else 'DRY-RUN'}: {changed} file(s) with merged-QID refs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
