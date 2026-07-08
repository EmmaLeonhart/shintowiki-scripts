#!/usr/bin/env python3
"""
collect_ronsha_rankings.py
===========================
Collector for the ronsha_ranking_review cloud-RAG queue (sibling of
collect_label_typo_answers.py). Scans `ronsha_ranking_review/*.wiki` for
filled `<!-- ANSWER: ... -->` markers:

  * `LIKELY: Qxxx` → emit P1352 qualifier-add lines onto the ronsha's P460
    statements: the named candidate gets 1, every other candidate gets 0
    (the binary convention on already-ranked ronsha). Lines are add-only and
    drip-safe; appended to modern-quickstatements/ronsha_ranking_qualifiers.txt.
  * `UNDECIDABLE: <note>` → logged to _undecidable.log, file deleted (Emma's
    review list keeps showing the item until she rules).

Candidate set is read from the work-file's own `* [[d:Qxxx]]` lines (frozen at
build time). Empty ANSWER → untouched. Processed files are deleted; resolved
ids logged to _resolved.log.

Usage: python collect_ronsha_rankings.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKDIR = os.path.join(ROOT, "ronsha_ranking_review")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "ronsha_ranking_qualifiers.txt")
RESOLVED = os.path.join(WORKDIR, "_resolved.log")
UNDECIDABLE = os.path.join(WORKDIR, "_undecidable.log")

ANSWER_RE = re.compile(r"<!--\s*ANSWER:\s*(.*?)\s*-->", re.S)
RONSHA_RE = re.compile(r"<!--\s*RONSHA:\s*https://www\.wikidata\.org/wiki/(Q\d+)")
CAND_RE = re.compile(r"^\*\s*\[\[d:(Q\d+)\]\]", re.M)


def parse(text):
    """(ronsha_qid, candidates, answer_kind, payload) or None if unanswered."""
    m = ANSWER_RE.search(text)
    if not m or not m.group(1).strip():
        return None
    ans = m.group(1).strip()
    ronsha = RONSHA_RE.search(text)
    cands = CAND_RE.findall(text)
    if not (ronsha and cands):
        return None
    k = re.match(r"(LIKELY|UNDECIDABLE)\s*:\s*(.*)", ans, re.S)
    if not k:
        return (ronsha.group(1), cands, "MALFORMED", ans)
    return (ronsha.group(1), cands, k.group(1), k.group(2).strip())


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(WORKDIR):
        print("no ronsha_ranking_review/ dir; nothing to collect")
        return
    pending = resolved = undecidable = malformed = 0
    qs = []
    for fn in sorted(os.listdir(WORKDIR)):
        if not fn.endswith(".wiki"):
            continue
        path = os.path.join(WORKDIR, fn)
        got = parse(open(path, encoding="utf-8").read())
        if got is None:
            pending += 1
            continue
        ronsha, cands, kind, payload = got
        if kind == "LIKELY":
            pick = re.search(r"Q\d+", payload)
            if not pick or pick.group(0) not in cands:
                malformed += 1
                print(f"MALFORMED (LIKELY not among candidates) in {fn}: {payload!r}")
                continue
            # Emma 2026-07-08: P1352=0 means "legitimate shrine present on
            # Wikipedia but NOT in the Kokugakuin database" — NOT "disproven".
            # Only the chosen candidate gets a rank; the others keep their
            # existing/absent ranks (zeroing them would fabricate a claim
            # about Kokugakuin coverage).
            qs.append(f"{ronsha}|P460|{pick.group(0)}|P1352|1")
            resolved += 1
            if not args.dry_run:
                with open(RESOLVED, "a", encoding="utf-8") as f:
                    f.write(f"{ronsha} LIKELY {pick.group(0)}\n")
                os.remove(path)
        elif kind == "UNDECIDABLE":
            undecidable += 1
            if not args.dry_run:
                with open(UNDECIDABLE, "a", encoding="utf-8") as f:
                    f.write(f"{ronsha} {payload}\n")
                os.remove(path)
        else:
            malformed += 1
            print(f"MALFORMED answer in {fn}: {payload!r}")
    if qs and not args.dry_run:
        with open(QS_OUT, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(qs) + "\n")
    print(f"pending={pending} resolved={resolved} undecidable={undecidable} "
          f"malformed={malformed} qs-lines={len(qs)}{' [DRY]' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
